import socket
import threading
import random
import sys
import json


class CollectorServer:
    def __init__(self, host, port, total_voters, is_collector1):
        self.host = host
        self.port = port
        self.total_voters = total_voters
        self.is_collector1 = is_collector1
        self.received_ballots = []  # Store received secret ballots
        self.random_shares = []  # Store random shares generated for voters
        self.lock = threading.Lock()  # Thread-safe access
        self.secret_ballot_aggregate = [0, 0]  # Aggregate of secret ballots
        self.random_share_aggregate = [0, 0]  # Aggregate of random shares
        self.peer_random_share_aggregate = [0, 0]  # Aggregate received from peer
        self.stop_accepting = False  # Signal to stop accepting connections
        self.candidates, _ = self.fetch_election_details()  # Fetch candidates dynamically

        # Generate random shares for location shares
        self.location_shares = self.generate_unique_location_shares()

    @staticmethod
    def fetch_election_details(config_file="election_config.json"):
        """
        Fetch candidates and voter count from the election configuration file.
        """
        try:
            with open(config_file, "r") as file:
                config = json.load(file)
                candidates = config["candidates"]
                total_voters = config["total_voters"]
                return candidates, total_voters
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_file}' not found.")
            sys.exit(1)
        except KeyError as e:
            print(f"Error: Missing key in configuration file: {e}")
            sys.exit(1)

    def generate_random_shares(self):
        """
        Generate two random shares for a voter.
        """
        random_share_1 = random.randint(1, 10)
        random_share_2 = random.randint(1, 10)
        self.random_shares.append((random_share_1, random_share_2))
        return random_share_1, random_share_2

    def generate_location_shares(self):
        """
        Generate random shares for location share calculation.
        """
        shares = []
        for _ in range(self.total_voters):
            share = random.randint(-10, 10)  # Random partial share
            shares.append(share)
        return shares

    def generate_unique_location_shares(self):
        """
        Generate unique random shares for all voters.
        Each voter gets a unique final location after combining shares.
        """
        shares = []
        while len(shares) < self.total_voters:
            share = random.randint(-10 * self.total_voters, 10 * self.total_voters)  # Ensure a wide range
            if share not in shares:
                shares.append(share)
        return shares

    def handle_voter(self, conn):
        """
        Handle communication with a voter or peer.
        """
        try:
            data = conn.recv(1024).decode().strip()
            if data.startswith("AGGREGATE"):  # Message from peer collector
                self.handle_peer_message(data)
            else:  # Voter message
                self.handle_voter_message(data, conn)
        except Exception as e:
            print(f"Error handling voter or peer: {e}")
        finally:
            conn.close()

    def tally_votes(self, final_result, candidates):
        """
        Tally votes from the final result based on binary representation and the candidate list.
        """
        candidate_count = len(candidates)
        voter_count = self.total_voters
        binary_length = voter_count * candidate_count

        # Process each number in the final result
        for i, number in enumerate(final_result):
            # Convert to binary, ensure it's the correct length
            binary_representation = bin(number)[2:].zfill(binary_length)

            # Reverse the binary string for the first number
            if i == 0:
                binary_representation = binary_representation[::-1]

            # Split into groups of `candidate_count` bits
            vote_splits = [binary_representation[j:j + candidate_count] for j in range(0, binary_length, candidate_count)]

            # Tally votes dynamically
            vote_counts = {candidate: 0 for candidate in candidates}
            for split in vote_splits:
                for idx, bit in enumerate(split):
                    if bit == "1":
                        vote_counts[candidates[idx]] += 1

            # Print results for this number
            print(f"Votes from Result {i + 1}: " + ", ".join(f"{candidate} = {vote_counts[candidate]}" for candidate in candidates))
    
    def handle_voter_message(self, data, conn):
        """
        Handle messages from voters.
        """
        try:
            if "," in data:  # Received secret ballot
                n1, n2 = map(int, data.split(","))
                with self.lock:
                    self.received_ballots.append((n1, n2))
                print(f"Received Secret Ballot: n1 = {n1}, n2 = {n2}")
                conn.send("ACK".encode())  # Acknowledge receipt
            else:  # Voter requesting random shares
                voter_id = int(data)
                # Get the partial location share for the voter
                with self.lock:
                    location_share = self.location_shares[voter_id - 1]  # Adjust for 0-based indexing
                random_share_1, random_share_2 = self.generate_random_shares()
                # Prepare the response
                response = f"{location_share},{random_share_1},{random_share_2}"
                # Log the sent data
                if self.is_collector1:
                    print(f"Collector 1: Sent Location Share = {location_share}, Random Shares = {random_share_1}, {random_share_2} to Voter {voter_id}")
                else:
                    print(f"Collector 2: Sent Location Share = {location_share}, Random Shares = {random_share_1}, {random_share_2} to Voter {voter_id}")

                conn.send(response.encode())
        except Exception as e:
            print(f"Error processing voter message: {e}")


    def handle_peer_message(self, data):
        """
        Handle communication from peer collector.
        """
        try:
            if data.startswith("AGGREGATE"):
                _, peer_aggregate_1, peer_aggregate_2 = data.split(",")
                self.peer_random_share_aggregate = [int(peer_aggregate_1), int(peer_aggregate_2)]
                print(f"Received Random Share Aggregate from Peer: {self.peer_random_share_aggregate}\n")

                # Compute Collector's own aggregates
                self.compute_aggregates()

                # Perform the final calculation
                result = [
                    self.secret_ballot_aggregate[0] - self.random_share_aggregate[0] - self.peer_random_share_aggregate[0],
                    self.secret_ballot_aggregate[1] - self.random_share_aggregate[1] - self.peer_random_share_aggregate[1],
                ]

                # Print the results
                print(f"Secret Ballot Aggregate: {self.secret_ballot_aggregate}")
                print(f"Random Share Aggregate (Collector): {self.random_share_aggregate}")
                print(f"Peer Random Share Aggregate: {self.peer_random_share_aggregate}")
                print(f"Final Result: {result}")

                # Fetch dynamic candidates and tally votes
                self.tally_votes(result, self.candidates)
            else:
                print(f"Unknown message from peer: {data}")
        except Exception as e:
            print(f"Error processing peer message: {e}")

    def compute_aggregates(self):
        with self.lock:
            # Aggregate secret ballots
            if self.received_ballots:
                self.secret_ballot_aggregate = [
                    sum(x) for x in zip(*self.received_ballots)
                ]
            else:
                print("No Secret Ballots Received.")
            # Aggregate random shares
            if self.random_shares:
                self.random_share_aggregate = [
                    sum(x) for x in zip(*self.random_shares)
                ]
            else:
                print("No Random Shares Generated.")


    def send_to_peer(self, peer_host, peer_port):
        """
        Send random share aggregate to the peer collector.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                peer_socket.connect((peer_host, peer_port))
                aggregate_str = f"AGGREGATE,{self.random_share_aggregate[0]},{self.random_share_aggregate[1]}"
                peer_socket.sendall(aggregate_str.encode())
        except Exception as e:
            print(f"Error sending data to Peer: {e}")

    def accept_voter_connections(self, server):
        """
        Accept connections from voters until signaled to stop.
        """
        while not self.stop_accepting:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self.handle_voter, args=(conn,)).start()
            except OSError:
                break  # Socket closed

    def accept_peer_connection(self, peer_port):
        """
        Accept connection from Peer Collector and process peer communication.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_server:
            peer_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            peer_server.bind((self.host, peer_port))
            peer_server.listen(1)
            conn, _ = peer_server.accept()
            self.handle_voter(conn)  # Pass to general handler

    def start_server(self, peer_host, peer_send_port, peer_receive_port):
        """
        Start the collector server and coordinate the process.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(5)
            print(f"Collector Server started on {self.host}:{self.port} ({'Collector 1' if self.is_collector1 else 'Collector 2'})")

            # Thread to accept voter connections
            thread = threading.Thread(target=self.accept_voter_connections, args=(server,))
            thread.start()

            # Wait for all votes to be cast
            input("🔔 Press Enter after all voters have cast their ballots...\n\n")
            self.stop_accepting = True
            server.close()  # Stop accepting connections
            thread.join()

            # Compute aggregates after receiving all voter ballots
            self.compute_aggregates()

            if self.is_collector1:
                # Collector 1: Wait for aggregate from Collector 2, then send its aggregate back
                self.accept_peer_connection(peer_receive_port)
                self.send_to_peer(peer_host, peer_send_port)
            else:
                # Collector 2: Send aggregate to Collector 1, then wait for Collector 1's aggregate
                self.send_to_peer(peer_host, peer_send_port)
                self.accept_peer_connection(peer_receive_port)


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python3 collector.py <port> <is_collector1> <peer_host> <peer_send_port> <peer_receive_port>")
        sys.exit(1)

    HOST = "127.0.0.1"
    PORT = int(sys.argv[1])
    IS_COLLECTOR1 = sys.argv[2].lower() == "true"
    PEER_HOST = sys.argv[3]
    PEER_SEND_PORT = int(sys.argv[4])
    PEER_RECEIVE_PORT = int(sys.argv[5])
    candidates, TOTAL_VOTERS = CollectorServer.fetch_election_details()
    print(f"Election Details: \n 🗳️  Candidates = {candidates}, \n 👥 Total Voters = {TOTAL_VOTERS}")


    collector = CollectorServer(HOST, PORT, TOTAL_VOTERS, IS_COLLECTOR1)
    collector.start_server(PEER_HOST, PEER_SEND_PORT, PEER_RECEIVE_PORT)
