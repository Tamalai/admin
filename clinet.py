from openai import OpenAI
import streamlit as st
import json
import base64
import streamlit_authenticator as stauth
import yaml
import bcrypt
import os
import datetime
import time  # Added for time-based session_id generation
from streamlit_autorefresh import st_autorefresh

# Path to the JSON file where interactions are stored
file_path = "U:\\doc\\e.json"

# Path to the JSON file that contains json_files mapping
json_files_mapping_path = "C:\\Users\\edward\\doc\\json_files_mapping.json"

# Load the configuration from the YAML file
with open("C:\\Users\\edward\\doc\\credentialss.yaml", encoding='utf-8') as file:
    config = yaml.safe_load(file)

# Initialize the authenticator
authenticator = stauth.Authenticate(
    config['credentialss'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# Attempt to authenticate the user
name, authentication_status, username = authenticator.login('main')

# Check for admin login
admin_username = 'admin'
admin_password_hash = config['credentialss']['usernames']['admin']['password']
if username == admin_username and bcrypt.checkpw('admin'.encode('utf-8'), admin_password_hash.encode('utf-8')):
    name, authentication_status, username = (admin_username, True, admin_username)

# Load json_files mapping from the external JSON file
def load_json_files_mapping(mapping_path):
    try:
        with open(mapping_path, 'r', encoding='utf-8') as jf:
            return json.load(jf)
    except FileNotFoundError:
        st.error(f"Mapping file not found at {mapping_path}. Please ensure the file exists.")
        return {}
    except json.JSONDecodeError:
        st.error(f"Mapping file at {mapping_path} is not a valid JSON.")
        return {}

json_files = load_json_files_mapping(json_files_mapping_path)

def reset_topic_after_timeout():
    current_time = datetime.datetime.now()
    last_interaction = st.session_state.get('last_interaction', current_time)
    
    # Check if more than 5 minutes have passed since last interaction
    if (current_time - last_interaction).total_seconds() > 300:
        st.session_state.current_topic = 'default'
        print("Topic reset to default due to inactivity.")
    
    # Update the last interaction time
    st.session_state.last_interaction = current_time

def load_stop_words(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]

stop_words_path = "C:\\Users\\edward\\doc\\heb_stopwords.txt"  
stop_words = load_stop_words(stop_words_path)

def load_data(selected_option=None):
    if selected_option is None:
        # Default behavior: Choose the first non-default option
        for key in json_files:
            if key != "default":
                selected_option = key
                break
    json_file_path = json_files[selected_option]['path']

    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    json_documents = extract_text_from_json(json_data)

    return json_documents, json_data

def extract_text_from_json(json_data):
    text_list = []
    def extract_text(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                extract_text(value)
        elif isinstance(obj, list):
            for item in obj:
                extract_text(item)
        elif isinstance(obj, str):
            text_list.append(obj)

    extract_text(json_data)
    return text_list

documents, json_data = load_data()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

guidance_data = json_data

def json_to_string(data, depth=0):
    output = []
    if isinstance(data, dict):
        for key, value in data.items():
            output.append(" " * depth + str(key) + ":")
            output.append(json_to_string(value, depth + 2))
    elif isinstance(data, list):
        for item in data:
            output.append(json_to_string(item, depth + 2))
    else:
        return " " * depth + str(data)
    return "\n".join(output)

guidance_string = json_to_string(guidance_data)

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = ""

MAX_EXCHANGES = 6
def update_conversation_history(history, user_input, ai_response):
    exchanges = history.split('\n\n')
    # Use the user's full name instead of "Human"
    new_exchange = f"{st.session_state.user_full_name}: {user_input}\nAI Assistant: {ai_response}"
    exchanges.append(new_exchange)
    recent_exchanges = exchanges[-MAX_EXCHANGES:]

    with open("U:\\doc\\inputs_and_outputs", 'a', encoding='utf-8') as file:
        file.write(new_exchange + "\n\n")

    return '\n\n'.join(recent_exchanges)

if 'current_topic' not in st.session_state:
    st.session_state.current_topic = "default"

def load_input_json_mapping(file_path):
    mapping = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(':')
            if len(parts) == 2:
                keywords, json_file = parts
                for keyword in keywords.split(','):
                    mapping[keyword.strip()] = json_file.strip()
    return mapping

# Function to load JSON data
def load_json_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # If the data is empty or malformed, initialize it
            if not data or not isinstance(data, list) or not isinstance(data[0], list):
                return []  # Initialize as an empty list to start fresh
            return data[0]  # Return the inner list of session dictionaries
    except (json.JSONDecodeError, FileNotFoundError):
        # Return an empty list if the JSON file is empty, invalid, or missing
        return []

# Function to save JSON data
def save_json_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump([data], file, ensure_ascii=False, indent=4)  # Save data back as a nested list

# Function to update JSON with conversation including admin involvement and timestamps
def update_json_with_conversation(user_input, response, session_id, user_name, role="ai"):
    data = load_json_data(file_path)
    current_time = datetime.datetime.now().isoformat()
    new_interaction = {
        "session_id": session_id,
        "user": user_name,
        "message": user_input,
        "timestamp": current_time,  # Add timestamp for user message
    }

    if role == "ai":
        new_interaction["ai"] = {
            "message": response,
            "timestamp": current_time  # Add timestamp for AI response
        }
    elif role == "admin":
        # Admin comments are handled separately
        pass  # No additional action needed here

    new_interaction["comments"] = []
    new_interaction["admin_involved"] = role == "admin"
    new_interaction["new_user_message"] = True

    data.append(new_interaction)  # Always append the new interaction to the list
    save_json_data(file_path, data)  # Save data back as a nested list

# Function to check for admin comments
def check_for_admin_comments(session_id):
    data = load_json_data(file_path)
    new_comments = []
    for session in data:
        if session["session_id"] == session_id:
            comments = session.get("comments", [])
            for comment in comments:
                if not comment.get("comment_displayed", False):
                    comment["comment_displayed"] = True
                    save_json_data(file_path, data)
                    new_comments.append(comment["message"])
    return new_comments

# Function to display admin comments
def display_admin_comments():
    if 'admin_comments' in st.session_state:
        for comment in st.session_state.admin_comments:
            # Append admin comment to the chat history with a timestamp if not already added
            if not any(c['content'] == comment and c['role'] == 'admin' for c in st.session_state.chat_history):
                st.session_state.chat_history.append({
                    "timestamp": datetime.datetime.now().timestamp(),
                    "role": "admin",
                    "content": comment
                })
        st.session_state.admin_comments = []  # Clear after displaying

# Define the stream_openai_response function
def stream_openai_response(conversation_history, user_input, client, guidance_string, user_full_name):
    response_placeholder = st.empty()

    background_info = f"My name is {st.session_state.user_full_name}."

    # Only add the user's name at the start of the conversation for context.
    if not conversation_history:
        user_input = f"My name is {user_full_name}. " + user_input

    # Now, concatenate the guidance string with the conversation history and the current user input
    full_input = f"{background_info}\n{guidance_string}\n{conversation_history}\nUser: {user_input}"

    full_response = ""
    try:
        for response in client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": full_input}, {"role": "user", "content": user_input}],
            max_tokens=3000,
            temperature=0.9,
            stream=True,
        ):
            delta_content = response.choices[0].delta.content if response.choices[0].delta.content else ""
            full_response += delta_content
            response_placeholder.markdown(full_response)

    except Exception as e:
        st.error(f"An error occurred: {e}")

    return full_response

# Function to interpret the user's input and predict intent
def interpret_state(translated_text: str, conversation_history: str, client: OpenAI) -> str:
    # Generate a reasoning prompt for the first model with descriptions
    options_with_descriptions = "\n".join([
        f'- "{key}": "{info["description"]}"' for key, info in json_files.items()
    ])

    state_prompt = (
        f"Given the translated text and the conversation history, determine which option from the list is most appropriate for handling the user's request based on the descriptions below. Please provide only the option name.\n\n"
        f"Options:\n{options_with_descriptions}\n\n"
        f"Text: {translated_text}\n\n"
        f"Conversation History: {conversation_history}\n\n"
        f"Please provide only the option name."
    )

    # Request the model to interpret the user's intent
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that selects the most appropriate option based on the user's input."},
            {"role": "user", "content": state_prompt}
        ],
        max_tokens=250,
        temperature=0.7
    )

    # Get the selected option
    interpretation = response.choices[0].message.content.strip()

    # Print the selected option in the console for debugging
    print(f"Interpretation: {interpretation}")
    
    # Find the most appropriate JSON file from the options
    for key in json_files.keys():
        if key.lower() in interpretation.lower():
            print(f"Chosen JSON: {key}")
            return key  # Return the key of the JSON file chosen by the model
    
    # If no match, use the default JSON
    print("Chosen JSON: default")
    return 'default'

def langchain_bot(user_input, conversation_history, client, guidance_string, user_full_name):
    # Generate AI response
    lm_response = stream_openai_response(conversation_history, user_input, client, guidance_string, user_full_name)

    # Update the conversation history with the new exchange
    updated_history = update_conversation_history(conversation_history, user_input, lm_response)
    st.session_state.conversation_history = updated_history

    # Save the interaction to e.json using update_json_with_conversation
    session_id = st.session_state.session_id
    user_name = st.session_state.user_full_name
    update_json_with_conversation(user_input, lm_response, session_id, user_name, role="ai")

    # Check for admin comments after AI response
    new_comments = check_for_admin_comments(session_id)
    if new_comments:
        st.session_state.admin_comments.extend(new_comments)

    # Append assistant's response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": lm_response})

    return lm_response

if authentication_status is None:
    st.warning('נא להזין שם משתמש וסיסמה')

elif authentication_status is False:
    st.error('Username/password is incorrect')

if authentication_status:
    user_full_name = config['credentialss']['usernames'].get(username, {}).get('name', 'Unknown User')
    print("Authenticated user's full name:", user_full_name)

    # Store user_full_name in session_state
    st.session_state.user_full_name = user_full_name

    # Generate and store session_id
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"{username}{int(time.time())}"

    session_id = st.session_state.session_id  # For convenience

    def load_custom_css():
        custom_css = """
        <style>
        /* Style for the spinner */
        .stSpinner {
            position: fixed;  /* Fixed position */
            top: 20%;        /* Place it in the middle vertically */
            left: 35%;       /* Place it in the middle horizontally */
            transform: translate(-50%, -50%); /* Adjust the position accurately */
            z-index: 100;    /* Ensure it's on top */
        }

        /* Increase the size of the spinner */
        .stSpinner > div {
            width: 800px;    /* Width of the spinner */
            height: 400px;   /* Height of the spinner */
        }
        .stApp {
            direction: rtl;
            text-align: right;
            z-index: 1;
        }
        .stMarkdown p {
            text-align: right;
            direction: rtl;
            word-wrap: break-word;
        }
        .stChatMessage {
            direction: rtl;
            text-align: right;
        }
        </style>
        """
        st.markdown(custom_css, unsafe_allow_html=True)

    # Call this function at the beginning of your app to load the custom styles
    load_custom_css()

    def set_images_and_background(logo_path: str, tamal_path: str):
        try:
            with open(logo_path, "rb") as logo_file:
                logo_encoded = base64.b64encode(logo_file.read()).decode()
            with open(tamal_path, "rb") as tamal_file:
                tamal_encoded = base64.b64encode(tamal_file.read()).decode()
        except FileNotFoundError as e:
            st.error(f"Image file not found: {e}")
            logo_encoded = ""
            tamal_encoded = ""

        css = """
        <style>
        .logo-section {
            position: fixed;
            right: 35px;
            bottom: -20px;
            z-index: 10;
        }
        .tamal-section {
            position: absolute;
            left: -660px;
            top: 0px;
            z-index: 10;
        }
        .color-section {
            position: fixed;
            left: 0;
            top: 0;
            width: 25%;
            height: 100vh;
            background-color: rgb(88,165,200);
            z-index: 5;
        }
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
        st.markdown('<div class="color-section"></div>', unsafe_allow_html=True)
        if logo_encoded:
            st.markdown(f'<div class="logo-section"><img src="data:image/png;base64,{logo_encoded}" alt="Logo" width="400px" height="300px"></div>', unsafe_allow_html=True)
        if tamal_encoded:
            st.markdown(f'<div class="tamal-section"><img src="data:image/png;base64,{tamal_encoded}" alt="Tamal"></div>', unsafe_allow_html=True)

    # Apply custom styles and images
    set_images_and_background("C:\\Users\\edward\\images\\logo.png", "C:\\Users\\edward\\images\\tamal.png")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    if 'display_chat' not in st.session_state:
        st.session_state.display_chat = True

    if 'admin_comments' not in st.session_state:
        st.session_state.admin_comments = []

    # Check if admin is involved
    data = load_json_data(file_path)
    admin_involved = any(session.get('admin_involved', False) for session in data if session['session_id'] == session_id)
    
    # Custom CSS to ensure the admin message is always on top
    if admin_involved:
        st.markdown(
            """
            <style>
            .admin-header {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                background-color: #ffcc00;
                text-align: center;
                z-index: 100;
                padding: 10px;
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            </style>
            """, unsafe_allow_html=True)

        # Display the admin header
        st.markdown('<div class="admin-header">אדמין הצטרף לשיחה</div>', unsafe_allow_html=True)
    
    # Title of the app (only shown if no admin is involved)
    if not admin_involved:
        st.title("💬 טמל-A.I")

    # Display chat history
    if st.session_state.display_chat:
        for msg in st.session_state.chat_history:
            role = msg["role"]
            content = msg["content"]
            st.chat_message(role).write(content)

    if admin_involved:
        st.subheader("אדמין הצטרף לשיחה")

        admin_input_key = f"user_input_{st.session_state.session_id}"
        
        # Initialize last_admin_message in session_state if not present
        last_admin_message_key = f'last_admin_message_{st.session_state.session_id}'
        if last_admin_message_key not in st.session_state:
            st.session_state[last_admin_message_key] = None

        # Input field for user to send a message to the admin
        admin_message = st.chat_input(placeholder="Type your message here...", key=admin_input_key)

        if admin_message and admin_message != st.session_state[last_admin_message_key]:
            st.session_state[last_admin_message_key] = admin_message  # Update last processed admin message

            # Log the user input during admin interaction and append to chat history
            st.session_state.chat_history.append({
                "timestamp": datetime.datetime.now().timestamp(),
                "role": "user",
                "content": admin_message
            })
            
            # Define user_name variable
            user_name = st.session_state.user_full_name
            
            # Log the user input during admin interaction
            update_json_with_conversation(admin_message, "", session_id, user_name, role="admin")
        
            st.experimental_rerun()  # Rerun to update the chat history immediately

    else:
        # Initialize last_prompt in session_state if not present
        if 'last_prompt' not in st.session_state:
            st.session_state.last_prompt = None

        # User input section
        prompt = st.chat_input("כתוב כאן:")
        if prompt and prompt != st.session_state.last_prompt:
            st.session_state.last_prompt = prompt  # Update last processed prompt

            # Call the reset function immediately after receiving prompt to manage session state
            reset_topic_after_timeout()

            # Display the user's message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Append to chat history
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            with st.spinner('מקליד/ה..'):
                # Use interpret_state to determine which JSON file to use based on the user input
                selected_option = interpret_state(prompt, st.session_state.conversation_history, client)
                
                # Load the appropriate data and update guidance_string
                documents, json_data = load_data(selected_option)
                guidance_string = json_to_string(json_data)

                lm_response = langchain_bot(prompt, st.session_state.conversation_history, client, guidance_string, user_full_name)

    # Auto-refresh every 5 seconds to check for new admin comments
    refresh_count = st_autorefresh(interval=5000, key="datarefresh")

    # Check for new comments on auto-refresh
    if refresh_count > 0:  # Ensure it runs only after the first refresh
        new_comments = check_for_admin_comments(session_id)
        if new_comments:
            st.session_state.admin_comments.extend(new_comments)
    
    # Display the admin comments after checking for updates
    display_admin_comments()

    # Ensure that the conversation history is maintained
    st.session_state.conversation_history = st.session_state.conversation_history
