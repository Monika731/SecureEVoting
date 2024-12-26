import json
import os

class ElectionAdministration:
    def __init__(self, config_file="election_config.json"):
        self.config_file = config_file
        self.election_config = {
            "candidates": ["R", "D", "X", "Y"],  # Add more candidates as needed
            "total_voters": 3  # Number of voters
        }

    def setup_election(self):
        """
        Write election configuration to a shared file.
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.election_config, f, indent=4)
            print(f"✅ Election setup completed successfully!")
        except Exception as e:
            print(f"❌ Error during election setup: {e}")

    def show_election_details(self):
        """
        Display the election configuration.
        """
        print("\n📊 Election Details:")
        print("=" * 30)
        print(f"🗳️  Candidates: {', '.join(self.election_config['candidates'])}")
        print(f"👥 Total Voters: {self.election_config['total_voters']}")
        print("=" * 30)

if __name__ == "__main__":
    print("\n=== 🗳️ Election Administration System ===")
    print("Setting up the election configuration...\n")
    ea = ElectionAdministration()
    ea.setup_election()
    ea.show_election_details()