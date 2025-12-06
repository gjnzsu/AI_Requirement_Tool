"""
Enhanced LLM-powered Chatbot.

This chatbot uses the multi-provider LLM infrastructure to provide
intelligent conversational responses.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm import LLMRouter, LLMProviderManager
from config.config import Config


class Chatbot:
    """
    Enhanced chatbot using LLM providers for intelligent conversations.
    
    Features:
    - Multi-provider LLM support (OpenAI, Gemini, DeepSeek)
    - Conversation history/memory
    - Automatic fallback to backup providers
    - Configurable system prompts
    """
    
    def __init__(self, 
                 provider_name: Optional[str] = None,
                 use_fallback: bool = True,
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.7,
                 max_history: int = 10):
        """
        Initialize the chatbot.
        
        Args:
            provider_name: LLM provider to use ('openai', 'gemini', 'deepseek').
                          If None, uses Config.LLM_PROVIDER
            use_fallback: Whether to enable automatic fallback to backup providers
            system_prompt: Custom system prompt. If None, uses default
            temperature: Sampling temperature (0.0 to 1.0). Higher = more creative
            max_history: Maximum number of conversation turns to keep in memory
        """
        self.provider_name = provider_name or Config.LLM_PROVIDER.lower()
        self.use_fallback = use_fallback
        self.temperature = temperature
        self.max_history = max_history
        
        # Default system prompt
        self.system_prompt = system_prompt or (
            "You are a helpful, friendly, and knowledgeable AI assistant. "
            "You provide clear, concise, and accurate responses. "
            "You are conversational and engaging while being professional."
        )
        
        # Conversation history: list of {"role": "user"/"assistant", "content": "..."}
        self.conversation_history: List[Dict[str, str]] = []
        
        # Initialize LLM provider
        self.llm_provider = None
        self.provider_manager = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the LLM provider(s) based on configuration."""
        try:
            # Get API key and model for primary provider
            api_key = Config.get_llm_api_key()
            model = Config.get_llm_model()
            
            if not api_key:
                raise ValueError(
                    f"No API key found for provider '{self.provider_name}'. "
                    f"Please set the appropriate API key in your environment variables."
                )
            
            # Create primary provider
            primary_provider = LLMRouter.get_provider(
                provider_name=self.provider_name,
                api_key=api_key,
                model=model
            )
            
            # Create fallback providers if enabled
            fallback_providers = []
            if self.use_fallback:
                fallback_providers = self._create_fallback_providers()
            
            # Use provider manager if fallbacks are available, otherwise use primary directly
            if fallback_providers:
                self.provider_manager = LLMProviderManager(
                    primary_provider=primary_provider,
                    fallback_providers=fallback_providers
                )
                self.llm_provider = None  # Use manager instead
            else:
                self.llm_provider = primary_provider
                self.provider_manager = None
            
            print(f"✓ Initialized LLM provider: {self.provider_name} ({model})")
            sys.stdout.flush()
            if fallback_providers:
                print(f"✓ Fallback providers enabled: {len(fallback_providers)}")
                sys.stdout.flush()
                
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize LLM provider: {e}\n"
                f"Please check your configuration and API keys."
            )
    
    def _create_fallback_providers(self) -> List:
        """Create fallback providers from available API keys."""
        fallbacks = []
        
        # Try to add other providers as fallbacks
        providers_to_try = ['openai', 'gemini', 'deepseek']
        providers_to_try.remove(self.provider_name.lower())
        
        for provider in providers_to_try:
            try:
                if provider == 'openai' and Config.OPENAI_API_KEY:
                    fallback = LLMRouter.get_provider(
                        provider_name='openai',
                        api_key=Config.OPENAI_API_KEY,
                        model=Config.OPENAI_MODEL
                    )
                    fallbacks.append(fallback)
                elif provider == 'gemini' and Config.GEMINI_API_KEY:
                    fallback = LLMRouter.get_provider(
                        provider_name='gemini',
                        api_key=Config.GEMINI_API_KEY,
                        model=Config.GEMINI_MODEL
                    )
                    fallbacks.append(fallback)
                elif provider == 'deepseek' and Config.DEEPSEEK_API_KEY:
                    fallback = LLMRouter.get_provider(
                        provider_name='deepseek',
                        api_key=Config.DEEPSEEK_API_KEY,
                        model=Config.DEEPSEEK_MODEL
                    )
                    fallbacks.append(fallback)
            except Exception:
                # Skip if provider can't be initialized
                continue
        
        return fallbacks
    
    def _build_prompt(self, user_input: str) -> str:
        """
        Build the full prompt including conversation history.
        
        Args:
            user_input: Current user message
            
        Returns:
            Formatted prompt string
        """
        # Build context from conversation history
        context_parts = []
        
        # Add recent conversation history (last max_history turns)
        recent_history = self.conversation_history[-self.max_history * 2:]  # *2 because each turn has user + assistant
        for msg in recent_history:
            role = msg['role']
            content = msg['content']
            if role == 'user':
                context_parts.append(f"User: {content}")
            elif role == 'assistant':
                context_parts.append(f"Assistant: {content}")
        
        # Add current user input
        context_parts.append(f"User: {user_input}")
        context_parts.append("Assistant:")
        
        # Combine system prompt with conversation context
        full_prompt = "\n".join(context_parts)
        return full_prompt
    
    def get_response(self, user_input: str) -> str:
        """
        Get a response from the LLM for the given user input.
        
        Args:
            user_input: User's message
            
        Returns:
            AI assistant's response
        """
        if not user_input.strip():
            return "I'm here! What would you like to talk about?"
        
        # Check for exit commands
        user_input_lower = user_input.lower().strip()
        if user_input_lower in ['bye', 'exit', 'quit', 'goodbye']:
            return "Goodbye! It was great chatting with you. Have a wonderful day!"
        
        try:
            # Build prompt with conversation history
            user_prompt = self._build_prompt(user_input)
            
            # Generate response using provider manager or direct provider
            if self.provider_manager:
                response = self.provider_manager.generate_response(
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.temperature,
                    json_mode=False
                )
            else:
                response = self.llm_provider.generate_response(
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.temperature,
                    json_mode=False
                )
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Trim history if it exceeds max_history
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            return response
            
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            print(f"\n[Error: {e}]", file=sys.stderr)
            return error_msg
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print("Conversation history cleared.")
    
    def get_history_summary(self) -> str:
        """Get a summary of the conversation history."""
        if not self.conversation_history:
            return "No conversation history yet."
        
        turns = len(self.conversation_history) // 2
        return f"Conversation has {turns} turn(s) in history."
    
    def run(self):
        """
        Run the chatbot in interactive mode.
        """
        print("=" * 70)
        print("🤖 LLM-Powered Chatbot")
        print("=" * 70)
        print(f"Provider: {self.provider_name}")
        print(f"Model: {Config.get_llm_model()}")
        print(f"Temperature: {self.temperature}")
        print(f"Max History: {self.max_history} turns")
        print("\nCommands:")
        print("  - Type your message and press Enter")
        print("  - Type 'bye', 'exit', or 'quit' to end the conversation")
        print("  - Type '/clear' to clear conversation history")
        print("  - Type '/history' to see conversation summary")
        print("=" * 70)
        print()
        
        # Simple greeting without API call to avoid blocking
        print("Chatbot: Hello! I'm ready to chat. How can I help you today?\n")
        sys.stdout.flush()
        
        # Main conversation loop
        while True:
            try:
                # Ensure prompt is displayed
                sys.stdout.flush()
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() == '/clear':
                    self.clear_history()
                    continue
                elif user_input.lower() == '/history':
                    print(f"Chatbot: {self.get_history_summary()}\n")
                    continue
                
                # Get and display response
                response = self.get_response(user_input)
                print(f"Chatbot: {response}\n")
                
                # Check if user wants to exit
                if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\nChatbot: Goodbye! Thanks for chatting!")
                break
            except EOFError:
                print("\n\nChatbot: Goodbye! Thanks for chatting!")
                break
            except Exception as e:
                print(f"\n[Unexpected error: {e}]\n")


def main():
    """Main entry point for the chatbot."""
    try:
        print("Initializing chatbot...")
        sys.stdout.flush()
        
        # Validate configuration
        if not Config.validate():
            print("⚠ Warning: Configuration validation failed.")
            print("Some features may not work correctly.")
            print("Please check your environment variables or .env file.\n")
            sys.stdout.flush()
        
        print("Creating chatbot instance...")
        sys.stdout.flush()
        
        # Create and run chatbot
        chatbot = Chatbot(
            provider_name=None,  # Use default from Config
            use_fallback=True,
            temperature=0.7,
            max_history=10
        )
        
        print("Starting chatbot...")
        sys.stdout.flush()
        
        chatbot.run()
        
    except Exception as e:
        print(f"\n❌ Failed to start chatbot: {e}")
        print("\nPlease ensure:")
        print("  1. Required dependencies are installed: pip install -r requirements.txt")
        print("  2. LLM_PROVIDER environment variable is set (e.g., 'openai', 'gemini', 'deepseek')")
        print("  3. Appropriate API key is set (e.g., OPENAI_API_KEY, GEMINI_API_KEY, DEEPSEEK_API_KEY)")
        print("  4. Model name is set (e.g., OPENAI_MODEL, GEMINI_MODEL, DEEPSEEK_MODEL)")
        sys.exit(1)


if __name__ == "__main__":
    main()