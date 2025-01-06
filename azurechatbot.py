import streamlit as st
import pandas as pd
import mysql.connector
import openai

# Set your OpenAI API key
api_key = st.text_input("Enter your OpenAI API key:", type="password", placeholder="sk-...")

# Ensure the user enters the API key
if not api_key:
    st.warning("Please enter your OpenAI API key to proceed.")
else:
    openai.api_key = api_key  # Set the user-provided API key

def fetch_table_schema(cursor, table_name):
    """
    Fetches the schema (column names and types) of a table from the database.
    """
    cursor.execute(f"DESCRIBE {table_name}")
    schema = cursor.fetchall()
    column_names = [col[0] for col in schema]
    return column_names

def generate_sql_query(user_prompt, column_names):
    """
    Generates an SQL SELECT query based on the user prompt and available column names.
    """
    try:
        # Format the column names as a string for the OpenAI model
        columns_description = ", ".join(column_names)
        schema_info = f"The table 'utilisation' has the following columns: {columns_description}."

        # Prompt for GPT-3.5 Turbo
        system_message = (
            "You are an expert SQL generator. "
            "You should only generate code that is supported in MySQL. "
            "Create only SQL SELECT queries based on the given description. "
            "The table always uses the name 'utilisation'. "
            "Only use the column names provided in the schema. "
            "Do not insert the SQL query as commented code. "
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{schema_info}\n\n{user_prompt}"}
        ]

        # Call the OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,  # Keep the response deterministic
            max_tokens=200  # Adjust depending on the expected query length
        )

        # Extract the SQL query from the response
        sql_query = response.choices[0].message['content'].strip()
        return sql_query
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"

# Streamlit UI

st.title("Insights Generator")

# Option to choose between different actions
uploaded_file = st.file_uploader("Upload your Excel file:", type=["xlsx"])

if st.button("REPLACE"):
    if uploaded_file is not None:
        with st.spinner("Processing..."):
            try:
                # Load the uploaded Excel file
                df = pd.read_excel(uploaded_file)
                df.columns = [col.strip().replace(" ", "").replace("/", "").replace("-", "") for col in df.columns]
                df = df.fillna("NULL")

                # Connect to the database
                connection = mysql.connector.connect(user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=True)
                cursor = connection.cursor()

                # Replace the 'utilisation' table
                cursor.execute(f"DROP TABLE IF EXISTS utilisation;")
                # st.write("Existing `utilisation` table has been dropped.")

                create_table_query = f"""
                CREATE TABLE utilisation (
                    {', '.join([f'`{col}` TEXT' for col in df.columns])}
                );
                """
                cursor.execute(create_table_query)
                # st.write("New `utilisation` table has been created.")

                # Insert data into the new 'utilisation' table
                for _, row in df.iterrows():
                    insert_query = f"INSERT INTO utilisation VALUES ({', '.join(['%s'] * len(row))})"
                    cursor.execute(insert_query, tuple(row))
                connection.commit()
                st.success("Data has been successfully uploaded and saved to the database.")
            except Exception as e:
                st.error(f"Error processing the file: {str(e)}")

# Text box for user input to query the database
user_query = st.text_input("Enter your query:")

if st.button("Get Result"):
    if user_query:
        try:
            # Connect to the database
            connection = mysql.connector.connect(user="nihal", password="Chotu0610", host="genaicogni.mysql.database.azure.com", port=3306, database="genai", ssl_ca="{ca-cert filename}", ssl_disabled=True)
            cursor = connection.cursor()

            # Fetch the table schema
            column_names = fetch_table_schema(cursor, "utilisation")

            # Generate the SQL query
            sql_query = generate_sql_query(user_query, column_names)

            # Execute the SQL query
            cursor.execute(sql_query)
            result = cursor.fetchall()

            # Display the result
            st.write(result)
        except Exception as e:
            st.error(f"Error executing the query: {str(e)}")
