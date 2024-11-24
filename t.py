import os
import json
import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# Function to format the timestamp
def format_timestamp(timestamp_str):
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
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
            timestamp = datetime.now().isoformat()

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
            icon: "https://i.imgur.com/5PhrjIb.png"  // החלף עם כתובת האייקון שלך
        }};
        var n = new Notification("הודעה חדשה ממשתמש", options);
    }} else {{
        console.log("התראות אינן מורשות.");
    }}
    </script>
    """
    components.html(js_code)

# Function to add custom CSS for styling
def load_custom_css():
    custom_css = """
    <style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    .stMarkdown p {
        text-align: right;
        direction: rtl;
        word-wrap: break-word;
    }
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

# Main function for the admin UI
def admin_ui():
    st.sidebar.title("פאנל אדמין")  # "Admin Panel" in Hebrew

    # Request notification permission
    request_notification_permission()

    # Set up auto-refresh every 3 seconds
    st_autorefresh(interval=3000, key="refresh")

    # Load data
    file_path = "U:\\doc\\e.json"  # שנה לנתיב הקובץ האמיתי שלך
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
                        timestamp = datetime.fromisoformat(timestamp_str)
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

# Add custom CSS for styling
def load_custom_css():
    custom_css = """
    <style>
    .stApp {
        direction: rtl;
        text-align: right;
    }
    .stMarkdown p {
        text-align: right;
        direction: rtl;
        word-wrap: break-word;
    }
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

# Entry point
if __name__ == "__main__":
    load_custom_css()
    admin_ui()
