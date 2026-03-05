import os

# Function to customize the menu order for games and specs
def customize_menu(games_path):
    # Retrieve all games directories
    games = [f for f in next(os.walk(games_path))[1] if not f.startswith('__')]

    # Prioritize World of Warcraft if it exists
    if 'World of Warcraft' in games:
        games.remove('World of Warcraft')
        games.insert(0, 'World of Warcraft')

    return games

# Function to customize the specs order for World of Warcraft
def customize_specs(specs):
    # Prioritize tank and wow specs if they exist
    priority_specs = ['tank', 'wow']
    ordered_specs = [spec for spec in priority_specs if spec in specs]
    other_specs = [spec for spec in specs if spec not in priority_specs]

    # Concatenate prioritized specs with the rest
    return ordered_specs + other_specs

# Example usage for integration with main.py
if __name__ == "__main__":
    games_path = './games'
    games = customize_menu(games_path)
    print("Customized Games List:")
    for game in games:
        print(game)

    # Example specs list for World of Warcraft
    specs = ['healer', 'dps', 'tank', 'wow']
    customized_specs = customize_specs(specs)
    print("\nCustomized Specs List for World of Warcraft:")
    for spec in customized_specs:
        print(spec)
