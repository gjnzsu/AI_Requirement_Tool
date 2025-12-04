def validate_input(user_input):
    if not user_input or not isinstance(user_input, str):
        raise ValueError("Invalid input: Input must be a non-empty string.")
    return user_input.strip()

def format_response(response):
    return response.strip() if response else "I'm sorry, I didn't understand that."

def log_message(message):
    with open("chatbot.log", "a") as log_file:
        log_file.write(f"{message}\n")