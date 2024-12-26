import socket
import sys
import json
import os
from threading import Lock


class VoterClient:
    ASSIGNED_SHARES_FILE = "assigned_shares.json"
    lock = Lock()  # Thread-safe access to the shared file

    def __init__(self, voter_id, vote, total_voters, total_candidates, collectors):
        self.voter_id = voter_id
        self.vote = vote
        self.total_voters = total_voters
        self.total_candidates = total_candidates
        self.voting_vector_size = total_voters * total_candidates
        self.collectors = collectors
        self.location_share = None
        self.random_shares_collector1 = []
        self.random_shares_collector2 = []
        self.secret_ballot = []

    @staticmethod
    def fetch_election_details(config_file="election_config.json"):
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
                candidates = config["candidates"]
                total_voters = config["total_voters"]
                print(f"Election Details: \n 🗳️  Candidates = {candidates}, \n 👥 Total Voters = {total_voters}")
                return candidates, total_voters
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file}' not found.")
            sys.exit(1)
        except KeyError as e:
            print(f"Error: Missing key in configuration file: {e}")
            sys.exit(1)

    @staticmethod
    def read_assigned_shares():
        """
        Read the assigned shares from the shared file.
        """
        if not os.path.exists(VoterClient.ASSIGNED_SHARES_FILE):
            return []
        with open(VoterClient.ASSIGNED_SHARES_FILE, "r") as file:
            return json.load(file)

    @staticmethod
    def write_assigned_shares(assigned_shares):
        """
        Write the updated assigned shares to the shared file.
        """
        with VoterClient.lock:
            with open(VoterClient.ASSIGNED_SHARES_FILE, "w") as file:
                json.dump(assigned_shares, file)

    @staticmethod
    def cleanup_assigned_shares(total_voters):
        """
        Delete the assigned shares file if all voters have been assigned their location shares.
        """
        assigned_shares = VoterClient.read_assigned_shares()
        if len(assigned_shares) == total_voters:
            os.remove(VoterClient.ASSIGNED_SHARES_FILE)


    def compute_voting_vector(self):
        voting_vector = [0] * self.voting_vector_size
        choice_index = self.vote
        voting_vector[(self.location_share - 1) * self.total_candidates + choice_index] = 1
        return voting_vector

    def compute_numbers(self, voting_vector):
        left_to_right = 0
        right_to_left = 0

        for i, val in enumerate(voting_vector):
            if val == 1:
                left_to_right = 2 ** i
                right_to_left = 2 ** (self.voting_vector_size - i - 1)
                break
        return left_to_right, right_to_left

    def receive_shares(self, collector, is_collector1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.connect(collector)
                client.sendall(str(self.voter_id).encode())  # Send voter ID
                response = client.recv(1024).decode().strip()

                # Parse the response
                parts = response.split(",")
                if len(parts) != 3:
                    raise ValueError(f"Unexpected response format: {response}")

                partial_location_share = int(parts[0])
                random_share_1 = int(parts[1])
                random_share_2 = int(parts[2])

                if is_collector1:
                    self.random_shares_collector1 = [random_share_1, random_share_2]
                    print(f"Collector 1: Partial Location Share = {partial_location_share}, Random Shares = {random_share_1}, {random_share_2}")
                else:
                    self.random_shares_collector2 = [random_share_1, random_share_2]
                    print(f"Collector 2: Partial Location Share = {partial_location_share}, Random Shares = {random_share_1}, {random_share_2}")

                return partial_location_share
        except Exception as e:
            print(f"Error receiving partial location shares: {e}")
            sys.exit(1)

    def vote_process(self):
        """
        Execute the voting process while ensuring unique location shares for each voter.
        :param assigned_shares: List of already assigned location shares.
        """
        location_share1 = self.receive_shares(self.collectors[0], True)  # From Collector 1
        location_share2 = self.receive_shares(self.collectors[1], False)  # From Collector 2

        # Compute the initial location share
        computed_share = (location_share1 + location_share2) % self.total_voters
        if computed_share == 0:
            computed_share = self.total_voters
        # Ensure uniqueness of the location share
        assigned_shares = self.read_assigned_shares()
        while computed_share in assigned_shares:
            computed_share = (computed_share + 1) % self.total_voters
            if computed_share == 0:
                computed_share = self.total_voters

        # Assign the unique location share
        self.location_share = computed_share
        assigned_shares.append(self.location_share)  # Update the shared list
        self.write_assigned_shares(assigned_shares)
        print(f"Voter {self.voter_id}: Unique Location Share = {self.location_share}")

        # Compute voting vector
        voting_vector = self.compute_voting_vector()
        print(f"Voter {self.voter_id}: Voting Vector = {voting_vector}")

        # Compute numbers from the voting vector
        number1, number2 = self.compute_numbers(voting_vector)
        print(f"Voter {self.voter_id}: Numbers from Voting Vector = [{number1}, {number2}]")

        # Compute secret ballot
        secret_number1 = number1 + self.random_shares_collector1[0] + self.random_shares_collector2[0]
        secret_number2 = number2 + self.random_shares_collector1[1] + self.random_shares_collector2[1]
        self.secret_ballot = [secret_number1, secret_number2]
        print(f"Voter {self.voter_id}: Secret Ballot = {self.secret_ballot}")

        # Send secret ballot to collectors
        self.send_secret_ballot()

        # Cleanup assigned_shares.json if all voters are assigned
        self.cleanup_assigned_shares(self.total_voters)


    def send_secret_ballot(self):
        for collector in self.collectors:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                    client.connect(collector)
                    ballot_str = f"{self.secret_ballot[0]},{self.secret_ballot[1]}"
                    client.sendall(ballot_str.encode())
                    response = client.recv(1024).decode()
            except Exception as e:
                print(f"Error connecting to Collector {collector}: {e}")


if __name__ == "__main__":
    print("\n🌟 Welcome to the Secure E-Voting System! 🛡️🗳️")
    print("==========================================")
    candidates, total_voters = VoterClient.fetch_election_details()

    voter_id = int(input("\n🔑 Please enter your unique Voter ID to proceed: "))

    print("Candidates:")
    for i, candidate in enumerate(candidates, start=1):
        print(f"{i}. {candidate}")

    vote_choice = None
    while vote_choice is None:
        try:
            vote_input = int(input(f"\n🎯 Please cast your vote by entering your choice (1-{len(candidates)}): ").strip())
            if 1 <= vote_input <= len(candidates):
                vote_choice = vote_input - 1  # Adjust to 0-based index
            else:
                print("Invalid input. Please select a valid option.")
        except ValueError:
            print("Invalid input. Please enter a number corresponding to your choice.")

    COLLECTORS = [("127.0.0.1", 65432), ("127.0.0.1", 65433)]
    voter = VoterClient(voter_id, vote_choice, total_voters, len(candidates), COLLECTORS)
    voter.vote_process()
