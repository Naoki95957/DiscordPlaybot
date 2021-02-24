from bot import PlayBot
from bot_terminal import BotTerminal    

def main():
    bot = PlayBot(threading=True, print_statements=False)
    terminal = BotTerminal(bot).start()
    
if __name__ == "__main__":
    main()