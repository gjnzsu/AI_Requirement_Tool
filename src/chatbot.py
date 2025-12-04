import random

class Chatbot:
    def __init__(self):
        self.greetings = ["Hello!", "Hi there!", "Greetings!", "How can I assist you today?"]
        self.farewells = ["Goodbye!", "See you later!", "Take care!", "Have a great day!"]

    def get_response(self, user_input):
        user_input = user_input.lower()
        if "hello" in user_input or "hi" in user_input:
            return random.choice(self.greetings)
        elif "bye" in user_input or "exit" in user_input:
            return random.choice(self.farewells)
        else:
            return "I'm sorry, I didn't understand that."

    def run(self):
        print("Chatbot is running! Type 'bye' to exit.")
        while True:
            user_input = input("You: ")
            response = self.get_response(user_input)
            print("Chatbot:", response)
            if response in self.farewells:
                break