import streamlit as st
from main import extract_nlu_info, fetch_schema, generate_prompt, call_groq_api, validate_and_correct_sql

# Streamlit UI
st.title("Natural Language to SQL Query Generator:RIGGER")

# User input for natural language query
nl_query = st.text_area("Enter your natural language query:")

if st.button("Generate SQL Query"):
    if nl_query:
        # Extract NLU Information
        nlu_info = extract_nlu_info(nl_query)
        
        # Fetch Schema
        schema_info = fetch_schema()
        
        # Generate Prompt
        prompt = generate_prompt(nl_query, schema_info)
        
        # Generate SQL Query
        generated_sql = call_groq_api(prompt)
        
        # Validate & Correct SQL
        validated_sql = validate_and_correct_sql(generated_sql, schema_info)
        
        # Display results
        st.subheader("Generated SQL Query:")
        st.code(generated_sql, language='sql')
        
        st.subheader("Validated SQL Query:")
        st.code(validated_sql, language='sql')
    else:
        st.warning("Please enter a natural language query.")
