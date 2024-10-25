import sys


def user_input() -> str:
    while True:
        user_input = input("> ")
        if len(user_input) > 0:
            break

    if user_input == "exit":
        sys.exit()
    return user_input
