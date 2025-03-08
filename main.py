# Import necessary libraries
import json
import requests
import psycopg2
import re

# Global variable to track token usage
total_tokens = 0

# PostgreSQL Connection Config (Update accordingly)
DB_CONFIG = {
    "dbname" : "postgres",
    "user" : "postgres",
    "password": "user",
    "host": "localhost",
    "port": "5432"
}

# Groq API Config
GROQ_API_KEY = "api key here"
GROQ_MODEL = "llama3-8b-8192"

# 1️⃣ Natural Language Understanding (NLU) Agent
def extract_nlu_info(nl_query):
    """
    Extracts user intent, attributes, and filtering conditions from an NL query.
    
    :param nl_query: User's natural language query.
    :return: Extracted intent, attributes, and filters.
    """
    keywords = re.findall(r'\b\w+\b', nl_query.lower())

    # Determine intent
    intent = "SELECT" if any(word in keywords for word in ["average", "sum", "count"]) else "UNKNOWN"

    # Extract possible filters based on common keywords
    filters = []
    if "time spent" in nl_query.lower():
        filters.append("time_spent_seconds")
    if "push notification clicked" in nl_query.lower():
        filters.append("push_notification_clicked = true")
    if "survey completed" in nl_query.lower():
        filters.append("survey_completed = true")

    return {
        "intent": intent,
        "attributes": keywords,
        "filters": filters
    }

# 2️⃣ Schema Extraction Agent (Enhanced)
def fetch_schema():
    """
    Connects to PostgreSQL and retrieves detailed schema information.
    
    :return: Dictionary containing table names, columns, data types, and primary keys.
    """
    schema_info = {}
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Fetch table names
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [table[0] for table in cursor.fetchall()]

        # Fetch column details for each table
        for table in tables:
            cursor.execute(f"""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = '{table}';
            """)
            columns = cursor.fetchall()

            # Extract primary keys
            cursor.execute(f"""
                SELECT k.column_name
                FROM information_schema.table_constraints t
                JOIN information_schema.key_column_usage k
                ON t.constraint_name = k.constraint_name
                WHERE t.table_name = '{table}' AND t.constraint_type = 'PRIMARY KEY';
            """)
            primary_keys = [pk[0] for pk in cursor.fetchall()]

            schema_info[table] = {
                "columns": {col[0]: col[1] for col in columns},  # Column Name: Data Type
                "primary_keys": primary_keys
            }

        conn.close()
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return {}

    return schema_info

# 3️⃣ Prompt Generation Agent (Improved)
def generate_prompt(nl_query, schema_info):
    """
    Generates a structured prompt using the NL query and enriched database schema.

    :param nl_query: Natural language query from the user.
    :param schema_info: Extracted database schema.
    :return: Structured prompt for SQL generation.
    """
    schema_details = "\n".join([
        f"Table: {table}\nColumns: {', '.join([f'{col} ({dtype})' for col, dtype in details['columns'].items()])}\nPrimary Keys: {', '.join(details['primary_keys'])}"
        for table, details in schema_info.items()
    ])

    prompt = (
        f"You are an SQL expert. Convert the following NL query into an optimized SQL query using this schema:\n\n"
        f"{schema_details}\n\n"
        f"NL Query: {nl_query}\n\n"
        f"SQL Query:"
    )
    return prompt

# 4️⃣ SQL Query Generation Agent
def call_groq_api(prompt):
    global total_tokens

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}"}
    data = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], 'temperature': 0.0, 'max_tokens': 300}

    response = requests.post(url, headers=headers, json=data)
    
    try:
        response_json = response.json()
        
        # Check if 'choices' exists in the response
        if 'choices' not in response_json:
            print("Error: API response does not contain 'choices'. Full response:", response_json)
            return None  # Return None to indicate failure
        
        total_tokens += response_json.get('usage', {}).get('completion_tokens', 0)
        sql_query = response_json['choices'][0]['message']['content']
        
        return sql_query

    except json.JSONDecodeError:
        print("Error: Failed to parse JSON response.")
        print("Raw response:", response.text)
        return None


# 5️⃣ Query Validation & Correction Agent (Enhanced)
def validate_and_correct_sql(sql_query, schema_info):
    """
    Validates and corrects an SQL query based on schema.
    
    :param sql_query: Generated SQL query.
    :param schema_info: Extracted schema to validate columns and tables.
    :return: Validated & corrected SQL query.
    """
    corrected_query = sql_query

    # Extract table and column names from query
    extracted_tables = re.findall(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)
    extracted_columns = re.findall(r'SELECT\s+(.*?)\s+FROM', sql_query, re.IGNORECASE)

    # Validate table names
    for table in extracted_tables:
        if table.lower() not in schema_info:
            print(f"⚠️ Error: Table '{table}' not found in schema. Attempting correction...")
            corrected_query = corrected_query.replace(table, list(schema_info.keys())[0])  # Replace with first valid table

    # Validate column names
    for col in extracted_columns:
        col_names = [c.strip().split(" ")[0] for c in col.split(",")]  # Handle aliases
        for c in col_names:
            if c.lower() not in [c.lower() for c in sum([list(details['columns'].keys()) for details in schema_info.values()], [])]:
                print(f"⚠️ Error: Column '{c}' not found in schema. Attempting correction...")
                first_valid_col = list(schema_info[list(schema_info.keys())[0]]['columns'].keys())[0]
                corrected_query = corrected_query.replace(c, first_valid_col)

    return corrected_query

# 🔹 Main Execution Pipeline
def main():
    nl_query = "Retrieve the loyalty_program_tier_level of customers who have reviewed a product referenced_product_identifier = 12345. Provide the review_unique_identifier and associated_review_image_urls."
    
    # 1️⃣ Extract NLU Information
    nlu_info = extract_nlu_info(nl_query)
    
    # 2️⃣ Fetch Schema (Enhanced)
    schema_info = fetch_schema()
    
    # 3️⃣ Generate Prompt (Improved)
    prompt = generate_prompt(nl_query, schema_info)
    
    # 4️⃣ Generate SQL Query
    generated_sql = call_groq_api(prompt)
    
    # 5️⃣ Validate & Correct SQL (Enhanced)
    validated_sql = validate_and_correct_sql(generated_sql, schema_info)

    print("\n🔷 NL Query:", nl_query)
    print("🔷 Generated SQL:", generated_sql)
    print("🔷 Validated SQL:", validated_sql)
    print("🔷 Total Tokens Used:", total_tokens)

    return validated_sql

if __name__ == "__main__":
    final_sql = main()
