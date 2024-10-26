from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List, Union, Any
from pymongo import MongoClient
import ollama
import json


app = Flask(__name__)
CORS(app)

from bson import ObjectId, Binary

def convert_to_json_compatible(data):
    """Recursively convert MongoDB BSON types to JSON-serializable formats."""
    if isinstance(data, dict):
        return {k: convert_to_json_compatible(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_json_compatible(item) for item in data]
    elif isinstance(data, ObjectId) or isinstance(data, Binary):
        return str(data)  # Convert ObjectId and Binary to string
    else:
        return data



class MongoDBLLMQueryGenerator:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/",
                 database: str = "louperdb",
                 model: str = "llama3.2") -> None:
        """Initialize the MongoDB LLM Query Generator.

        Args:
            mongo_uri: MongoDB connection string
            database: Database name
            model: LLM model name
        """
        self.client = MongoClient(mongo_uri)
        self.db = self.client[database]
        self.model = model

    def generate_query(self, user_input: str, collection_name: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Generate MongoDB query from natural language input."""
        system_prompt = f'''
        You are a MongoDB query generator expert specialized in subscription analytics.
        Convert natural language requests into valid MongoDB queries.
        Only respond with the actual query in JSON format, nothing else.
        The query will be used on the '{collection_name}' collection. Don't be type sensitive

        CRITICAL RULES:
        1. For simple find queries, just use $match without $project or other stages
        2. For counting queries, use ONLY $match and $count stages
        3. Never include empty $project stages
        4. Use exact field names and values

        Schema Fields:
        - type: pro, plus, free, studio, team
        - credits: number
        - creditsEnd: date
        - customerId: string
        - trial_activated: boolean
        
        and it has many more fields. use data from mongodb to send relevant results.

        Example Queries:


        Now based on the info provided to you generate a query for: {user_input}
        '''
        try:
            response = ollama.chat(model=self.model, messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ])

            query_str = response['message']['content'].strip()
            query_str = query_str.replace('```json', '').replace('```', '').strip()
            return json.loads(query_str)

        except Exception as e:
            raise Exception(f"Query generation error: {str(e)}")

    def execute_query(self, collection_name: str, query: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[
        Dict[str, Any]]:
        """Execute MongoDB query."""
        try:
            collection = self.db[collection_name]

            if isinstance(query, list):
                results = list(collection.aggregate(query))
            elif "$match" in query:
                results = list(collection.find(query["$match"]))
            else:
                results = list(collection.find(query))

            return results

        except Exception as e:
            raise Exception(f"Query execution error: {str(e)}")

    def format_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format query results as JSON."""
        if not results:
            return {"status": "success", "message": "No matches found", "data": []}

        if len(results) == 1 and "total" in results[0]:
            return {
                "status": "success",
                "message": f"Count: {results[0]['total']} matches",
                "data": results
            }

        if len(results) > 0 and "_id" in results[0] and "count" in results[0]:
            formatted_results = [{"group": result["_id"], "count": result["count"]} for result in results]
            return {
                "status": "success",
                "message": "Group results",
                "data": formatted_results
            }

        # Clean up results by removing MongoDB-specific fields
        cleaned_results = []
        for result in results:
            if isinstance(result, dict):
                cleaned_result = {k: v for k, v in result.items() if k not in ["_id", "__v"]}
                cleaned_results.append(cleaned_result)

        return {
            "status": "success",
            "message": f"Found {len(cleaned_results)} matches",
            "data": cleaned_results
        }

    def query(self, user_input: str, collection_name: str = "users") -> Dict[str, Any]:
        """Process natural language query and return formatted results."""
        try:
            query = self.generate_query(user_input, collection_name)
            results = self.execute_query(collection_name, query)
            return self.format_results(results)
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }

    def __del__(self) -> None:
        """Cleanup database connection."""
        try:
            self.client.close()
        except:
            pass


# Create a single instance of the query generator
query_generator = MongoDBLLMQueryGenerator(
    mongo_uri="mongodb://localhost:27017/",
    database="louperdb",
    model="llama3.2"
)


@app.route('/api/query', methods=['POST'])
def process_query():
    """API endpoint to process natural language queries."""
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing 'query' in request body",
                "data": None
            }), 400

        user_query = data['query']
        collection_name = data.get('collection', 'users')  # Default to 'users' if not specified

        result = query_generator.query(user_query, collection_name)
        # Convert result to JSON-compatible format
        result = convert_to_json_compatible(result)
        return jsonify(result)

    except Exception as e:
        # Log stack trace for debugging
        print("Error occurred:", traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}",
            "data": None
        }), 500


@app.route('/api/health', methods=['POST'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "success",
        "message": "Server is running",
        "data": {
            "service": "MongoDB LLM Query Generator",
            "database": query_generator.db.name,
            "model": query_generator.model
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
