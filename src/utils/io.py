def user_input() -> str:
    while True:
        user_input = input("> ")
        if len(user_input) > 0:
            break
    return user_input
