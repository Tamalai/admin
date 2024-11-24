import os
import json
import yaml
import datetime
import time
import bcrypt
import base64
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth
import streamlit.components.v1 as components
from openai import OpenAI  # Make sure to install the OpenAI package

# Paths to necessary files
CREDENTIALS_FILE = "C:\\Users\\edward\\doc\\credentialss.yaml"
E_JSON_FILE = "U:\\doc\\e.json"
JSON_FILES_MAPPING_FILE = "C:\\Users\\edward\\doc\\json_files_mapping.json"
STOP_WORDS_FILE = "C:\\Users\\edward\\doc\\heb_stopwords.txt"
LOGO_PATH = "C:\\Users\\edward\\images\\logo.png"
TAMAL_PATH = "C:\\Users\\edward\\images\\tamal.png"

# Load the configuration from the YAML file
with open(CREDENTIALS_FILE, encoding='utf-8') as file:
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

def load_custom_css():
    custom_css = """
    <style>
    /* Spinner styles */
    .stSpinner {
        position: fixed;
        top: 20%;
        left: 35%;
        transform: translate(-50%, -50%);
        z-index: 100;
    }
    .stSpinner > div {
        width: 800px;
        height: 400px;
    }
    /* General styles */
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
    /* Chat container styles */
    .chat-container {
        max-width: 600px;
        margin: 0 auto;
    }
    .message {
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
        width: fit-content;
        max-width: 70%;
        position: relative;
    }
    .user {
        background-color: #e2f0d9;
        align-self: flex-start;
    }
    .ai {
        background-color: #d9edf7;
        align-self: flex-end;
    }
    .admin {
        background-color: #f7e2d9;
        align-self: flex-end;
    }
    .timestamp {
        display: block;
        font-size: 0.8em;
        color: #555;
        margin-top: 5px;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def admin_interface():
    # Load necessary data
    load_custom_css()
    st.sidebar.title("פאנל אדמין")  # "Admin Panel" in Hebrew

    # Function to format the timestamp
    def format_timestamp(timestamp_str):
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp_str)
            return timestamp.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return "זמן לא ידוע"  # "Unknown Time" in Hebrew

    # Load JSON file
    def load_json_data(file_path):
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            data = []
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = []

        # Initialize new_user_message flag for each interaction if not already set
        for interaction_list in data:
            for interaction in interaction_list:
                if isinstance(interaction, dict):
                    if 'new_user_message' not in interaction:
                        interaction['new_user_message'] = False

        return data

    # Save JSON file
    def save_json_data(file_path, data):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    # Function to display all interactions in a continuous chat flow
    def display_all_interactions(session_id, data, file_path):
        # Filter interactions by session ID
        session_interactions = []
        for interaction_list in data:
            session_interactions.extend(
                [interaction for interaction in interaction_list if interaction.get('session_id') == session_id]
            )

        if not session_interactions:
            st.write("אין אינטראקציות זמינות.")  # "No interactions available for this session."
            return

        # Sort messages by timestamp in ascending order (oldest first)
        session_interactions.sort(key=lambda x: x.get('timestamp', ''))

        # Reset the new user message flag
        for interaction in session_interactions:
            if interaction.get('new_user_message', False):
                interaction['new_user_message'] = False

        # Save the changes
        save_json_data(file_path, data)

        # Display all messages in a continuous chat-like format
        st.write("<div class='chat-container'>", unsafe_allow_html=True)

        admin_involved = False  # Track if the admin is involved
        for interaction in session_interactions:
            # Check if admin is involved in the current session
            if interaction.get('admin_involved', False):
                admin_involved = True

            # Format the timestamp for user message
            timestamp_str = interaction.get('timestamp', '')
            formatted_time = format_timestamp(timestamp_str)

            # Display user message with timestamp
            user = interaction.get('user', 'Unknown')
            user_message = interaction.get('message', '') or ''
            st.markdown(
                f"""
                <div class='message user'>
                    <strong>משתמש ({user}):</strong> {user_message.replace('\\n', '<br>')}
                    <span class='timestamp'>{formatted_time}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Display AI assistant response only if it's non-empty, with timestamp
            ai_response = interaction.get('ai', {}).get('message', '') or ''
            ai_timestamp_str = interaction.get('ai', {}).get('timestamp', '')
            ai_formatted_time = format_timestamp(ai_timestamp_str)

            if ai_response.strip():
                st.markdown(
                    f"""
                    <div class='message ai'>
                        <strong>עוזר AI:</strong> {ai_response.replace('\\n', '<br>')}
                        <span class='timestamp'>{ai_formatted_time}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Display existing comments for this interaction
            if interaction.get('comments'):
                for comment in sorted(interaction['comments'], key=lambda c: c.get('timestamp', '')):
                    comment_time = format_timestamp(comment.get('timestamp', ''))
                    user_label = "מנהל" if comment.get("user") == "Admin" else f"משתמש ({comment.get('user', 'Unknown')})"
                    message_class = "admin" if comment.get("user") == "Admin" else "user"
                    st.markdown(
                        f"""
                        <div class='message {message_class}'>
                            <strong>{user_label}:</strong> {comment.get('message', '').replace('\\n', '<br>')}
                            <span class='timestamp'>{comment_time}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        st.write("</div>", unsafe_allow_html=True)

        # Add a chat input for admin comments at the bottom of the chat
        new_comment = st.chat_input("הוסף תגובה")  # "Add a comment" in Hebrew

        if new_comment:
            if new_comment.strip():
                timestamp = datetime.datetime.now().isoformat()

                # Add the new comment to the latest interaction in the session
                if session_interactions:
                    latest_interaction = session_interactions[-1]

                    if "comments" not in latest_interaction or not isinstance(latest_interaction["comments"], list):
                        latest_interaction["comments"] = []

                    latest_interaction['comments'].append({
                        "user": "Admin",
                        "message": new_comment,
                        "timestamp": timestamp,
                        "comment_displayed": False
                    })

                    # Mark that admin is involved
                    latest_interaction['admin_involved'] = True

                    # Save updated data back to JSON
                    save_json_data(file_path, data)

                    st.success("התגובה נוספה בהצלחה!")  # "Comment added successfully!"
                    st.experimental_rerun()
                else:
                    st.error("אין אינטראקציות זמינות להוספת תגובה.")  # "No interactions available to add the comment."

        # Show a button for the admin to return control back to the AI
        if admin_involved:
            if st.button("חזור ל-AI"):  # "Return to AI" in Hebrew
                # Mark admin involvement as False for all interactions in the session
                for interaction in session_interactions:
                    interaction['admin_involved'] = False

                # Save changes back to JSON
                save_json_data(file_path, data)

                st.success("השליטה הוחזרה ל-AI.")  # "Control returned to AI."
                st.experimental_rerun()

    # Function to request browser notification permission
    def request_notification_permission():
        # JavaScript code to request notification permission
        js_code = """
        <script>
        if ("Notification" in window) {
            if (Notification.permission !== "granted") {
                Notification.requestPermission().then(function(result) {
                    console.log("הרשאת התראות:", result);
                });
            }
        } else {
            console.log("הדפדפן אינו תומך בהתראות.");
        }
        </script>
        """
        components.html(js_code)

    # Function to send browser notification
    def send_browser_notification(message):
        # JavaScript code to send a notification
        js_code = f"""
        <script>
        if ("Notification" in window && Notification.permission === "granted") {{
            var options = {{
                body: "{message}",
                icon: "https://i.imgur.com/5PhrjIb.png"  // Replace with your icon URL
            }};
            var n = new Notification("הודעה חדשה ממשתמש", options);
        }} else {{
            console.log("התראות אינן מורשות.");
        }}
        </script>
        """
        components.html(js_code)

    # Main function for the admin UI
    def admin_ui():
        # Request notification permission
        request_notification_permission()

        # Set up auto-refresh every 3 seconds
        st_autorefresh(interval=3000, key="refresh")

        # Load data
        file_path = E_JSON_FILE  # Adjust to your actual file path
        data = load_json_data(file_path)

        # Extract unique session IDs and sort them with newest first, prioritize sessions with new messages
        unique_sessions = {}
        for interaction_list in data:
            for interaction in interaction_list:
                if isinstance(interaction, dict):
                    session_id = interaction.get('session_id')
                    if not session_id:
                        continue  # Skip if no session_id

                    if session_id not in unique_sessions:
                        unique_sessions[session_id] = {'has_new_message': False, 'last_timestamp': None}

                    # Check for new messages
                    if interaction.get('new_user_message', False):
                        unique_sessions[session_id]['has_new_message'] = True

                    # Update with the latest timestamp
                    timestamp_str = interaction.get('timestamp', '')
                    if timestamp_str:
                        try:
                            timestamp = datetime.datetime.fromisoformat(timestamp_str)
                            current_last_timestamp = unique_sessions[session_id]['last_timestamp']
                            if current_last_timestamp is None or timestamp > current_last_timestamp:
                                unique_sessions[session_id]['last_timestamp'] = timestamp
                        except ValueError:
                            pass  # Handle invalid timestamp format

        # --- Notification Logic ---
        # Maintain previous set of session IDs with new messages
        if 'prev_new_message_sessions' not in st.session_state:
            st.session_state.prev_new_message_sessions = set()

        # Get the current set of session IDs with new messages
        current_new_message_sessions = set()
        for session_id, session_info in unique_sessions.items():
            if session_info['has_new_message']:
                current_new_message_sessions.add(session_id)

        # Compare with the previous set
        new_sessions_with_new_messages = current_new_message_sessions - st.session_state.prev_new_message_sessions

        # Update the previous set
        st.session_state.prev_new_message_sessions = current_new_message_sessions

        # If there are new messages, send browser notification
        if new_sessions_with_new_messages:
            notification_message = "יש לך הודעה חדשה ממשתמש!"
            send_browser_notification(notification_message)
        # --- End of Notification Logic ---

        # Function to safely get timestamp number
        def get_timestamp_num(dt):
            if dt is None:
                return float('-inf')
            else:
                return dt.timestamp()

        # Sort sessions with new messages at the top and by last interaction timestamp (newest first)
        sorted_sessions = sorted(
            unique_sessions.items(),
            key=lambda x: (-int(x[1]['has_new_message']), -get_timestamp_num(x[1]['last_timestamp']))
        )

        # Sidebar for session navigation using buttons
        st.sidebar.subheader("שיחות משתמשים")  # "User Conversations" in Hebrew

        # Maintain session state for the selected session
        if 'selected_session_id' not in st.session_state:
            if sorted_sessions:
                st.session_state.selected_session_id = sorted_sessions[0][0]  # Default to the newest session
            else:
                st.session_state.selected_session_id = None  # No sessions available

        # Create buttons for sessions
        if sorted_sessions:
            for index, (session_id, session_info) in enumerate(sorted_sessions):
                # Add emoji to the button text if there's a new user message
                button_text = f"שיחה {session_id}"  # "Session {session_id}" in Hebrew
                if session_info['has_new_message']:
                    button_text = f"🟠 {button_text}"  # Orange circle emoji to indicate a new message

                # Ensure unique key for each button using index
                if st.sidebar.button(button_text, key=f"session_{index}", help="לחץ לצפייה בשיחה"):  # "Click to view session" in Hebrew
                    st.session_state.selected_session_id = session_id

                    # Reset the new user message flag
                    for interaction_list in data:
                        for interaction in interaction_list:
                            if isinstance(interaction, dict) and interaction.get('session_id') == session_id:
                                interaction['new_user_message'] = False
                    save_json_data(file_path, data)  # Save changes
        else:
            st.sidebar.write("אין שיחות זמינות.")  # "No sessions available." in Hebrew

        # Display interactions only if a session is selected
        selected_session_id = st.session_state.selected_session_id
        if selected_session_id:
            # Display interactions for the selected session
            display_all_interactions(selected_session_id, data, file_path)
        else:
            st.write("אין שיחות להצגה.")  # "No sessions to display." in Hebrew

    # Run the admin UI
    admin_ui()

def user_interface():
    load_custom_css()
    # Include the code from your user interface here
    # For brevity, I'll include the essential parts and adjust accordingly

    # Initialize variables and functions as per your user code
    # Make sure to adjust the paths and variables

    # Path to the JSON file where interactions are stored
    file_path = E_JSON_FILE

    # Path to the JSON file that contains json_files mapping
    json_files_mapping_path = JSON_FILES_MAPPING_FILE

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

    stop_words_path = STOP_WORDS_FILE
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

    # Begin user interface code
    user_full_name = config['credentialss']['usernames'][username]['name']
    print("Authenticated user's full name:", user_full_name)

    # Store user_full_name in session_state
    st.session_state.user_full_name = user_full_name

    # Generate and store session_id
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"{username}{int(time.time())}"

    session_id = st.session_state.session_id  # For convenience

    # Apply custom styles and images
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

    set_images_and_background(LOGO_PATH, TAMAL_PATH)

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

            # Append to chat history
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

# Main application logic
if authentication_status:
    if username == 'admin':
        admin_interface()
    else:
        user_interface()
elif authentication_status == False:
    st.error('Username/password is incorrect')
else:
    st.warning('Please enter your username and password')
