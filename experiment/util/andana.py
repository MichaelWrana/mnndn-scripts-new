from util.ndn import *

import pathlib
import random
import os
import sys

def share_symmetric_key(user, relay, verbose=False):
    print(f"Sharing symmetric key from {user.name} to {relay.name}\n")

    # user generates public key
    user.cmd(f"openssl genpkey -algorithm X25519 -out andana/{relay.name}.key")
    user.cmd(f"openssl pkey -in andana/{relay.name}.key -pubout -out andana/{user.name}_{relay.name}.pub")

    # relay generates public key
    relay.cmd(f"openssl genpkey -algorithm X25519 -out andana/{user.name}.key")
    relay.cmd(f"openssl pkey -in andana/{user.name}.key -pubout -out andana/{relay.name}_{user.name}.pub")

    # send user's public key to relay
    safe_putchunks(user, network_address=f"ndn/{user.name}-site/{user.name}/{user.name}_{relay.name}.pub", file_location=f"andana/{user.name}_{relay.name}.pub", verbose=False)
    safe_catchunks(relay, network_address=f"ndn/{user.name}-site/{user.name}/{user.name}_{relay.name}.pub", file_location=f"andana/{user.name}_{relay.name}.pub")

    # send relay's public key to user
    safe_putchunks(relay, network_address=f"ndn/{relay.name}-site/{relay.name}/{relay.name}_{user.name}.pub", file_location=f"andana/{relay.name}_{user.name}.pub", verbose=False)
    safe_catchunks(user, network_address=f"ndn/{relay.name}-site/{relay.name}/{relay.name}_{user.name}.pub", file_location=f"andana/{relay.name}_{user.name}.pub")

    # obtain a shared secret
    user.cmd(f"openssl pkeyutl -derive -inkey andana/{relay.name}.key -peerkey andana/{relay.name}_{user.name}.pub -out andana/{relay.name}_{user.name}.shared")
    relay.cmd(f"openssl pkeyutl -derive -inkey andana/{user.name}.key -peerkey andana/{user.name}_{relay.name}.pub -out andana/{user.name}_{relay.name}.shared")

    # user creates salt/info and sends to relay
    user.cmd(f"openssl rand -hex 16 | tr -d '\n' > andana/{relay.name}_{user.name}.salt")
    user.cmd(f"printf 'andana-symmetric-key' > andana/{relay.name}_{user.name}.info")

    # send salt to relay
    safe_putchunks(user, network_address=f"ndn/{user.name}-site/{user.name}/{relay.name}_{user.name}.salt", file_location=f"andana/{relay.name}_{user.name}.salt", verbose=False)
    safe_catchunks(relay, network_address=f"ndn/{user.name}-site/{user.name}/{relay.name}_{user.name}.salt", file_location=f"andana/{user.name}_{relay.name}.salt")

    # send info to relay
    safe_putchunks(user, network_address=f"ndn/{user.name}-site/{user.name}/{relay.name}_{user.name}.info", file_location=f"andana/{relay.name}_{user.name}.info", verbose=False)
    safe_catchunks(relay, network_address=f"ndn/{user.name}-site/{user.name}/{relay.name}_{user.name}.info", file_location=f"andana/{user.name}_{relay.name}.info")

    # derive the shared key using info, salt, and shared secret
    user_salt = user.cmd(f"xxd -p andana/{relay.name}_{user.name}.salt | tr -d '\n'")[2:]
    user_info = user.cmd(f"xxd -p andana/{relay.name}_{user.name}.info | tr -d '\n'")[2:]
    user_secret = user.cmd(f"xxd -p andana/{relay.name}_{user.name}.shared | tr -d '\n'")[2:]

    relay_salt = relay.cmd(f"xxd -p andana/{user.name}_{relay.name}.salt | tr -d '\n'")[2:]
    relay_info = relay.cmd(f"xxd -p andana/{user.name}_{relay.name}.info | tr -d '\n'")[2:]
    relay_secret = relay.cmd(f"xxd -p andana/{user.name}_{relay.name}.shared | tr -d '\n'")[2:]

    user_key = user.cmd(f"openssl kdf -binary -keylen 32 -kdfopt digest:sha256 -kdfopt salt:hex:{user_salt} -kdfopt info:hex:{user_info} -kdfopt key:hex:{user_secret} HKDF > andana/{relay.name}_{user.name}.sharedkey")
    relay_key = relay.cmd(f"openssl kdf -binary -keylen 32 -kdfopt digest:sha256 -kdfopt salt:hex:{relay_salt} -kdfopt info:hex:{relay_info} -kdfopt key:hex:{relay_secret} HKDF > andana/{user.name}_{relay.name}.sharedkey")

def send_andana_request(host, network_address, relay_list):

    sid = f"{time.time()}"
    andana_route = [host] + relay_list

    # create the interest
    host.cmd(f"echo {network_address} > andana/interest/{sid}")

    # encrypt layer-by-later for each relay:
    # TODO

    for i in range(len(andana_route)-1):
        current_user = andana_route[i]
        next_user = andana_route[i+1]
        safe_putchunks(current_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/interest/{sid}", file_location=f"andana/interest/{sid}", verbose=False)
        safe_catchunks(next_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/interest/{sid}", file_location=f"andana/interest/{sid}")

        # peel back one layer
        # TODO


    # issue the interest from exit relay
    safe_catchunks(andana_route[-1], network_address=network_address, file_location=f"andana/data/{sid}")

    for i in range(len(andana_route)-1, 0, -1):
        current_user = andana_route[i]
        next_user = andana_route[i-1]
        safe_putchunks(current_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/data/{sid}", file_location=f"andana/data/{sid}", verbose=False)
        safe_catchunks(next_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/data/{sid}", file_location=f"andana/data/{sid}")

        # add one layer
        # TODO

    # decrypt layer-by-layer in reverse order
    # TODO

    return

def send_andana_request_faster(host, network_address, relay_list):

    sid = f"{time.time()}"
    andana_route = [host] + relay_list

    # create the interest
    host.cmd(f"echo {network_address} > andana/interest/{sid}")

    # encrypt layer-by-later for each relay:
    # TODO

    for i in range(len(andana_route)-1):
        current_user = andana_route[i]
        next_user = andana_route[i+1]
        safe_putchunks(current_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/interest/{sid}", file_location=f"andana/interest/{sid}", verbose=False)
        safe_catchunks(next_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/interest/{sid}", file_location=f"andana/interest/{sid}")

        # peel back one layer
        # TODO


    # issue the interest from exit relay
    safe_catchunks(andana_route[-1], network_address=network_address, file_location=f"andana/data/{sid}")

    for i in range(len(andana_route)-1, 0, -1):
        current_user = andana_route[i]
        next_user = andana_route[i-1]
        safe_putchunks(current_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/data/{sid}", file_location=f"andana/data/{sid}", verbose=False)
        safe_catchunks(next_user, network_address=f"ndn/{current_user.name}-site/{current_user.name}/data/{sid}", file_location=f"andana/data/{sid}")

        # add one layer
        # TODO

    # decrypt layer-by-layer in reverse order
    # TODO

    return

class AndanaReplayer(NDNReplayer):
    def __init__(self, ndn_host, server_prefix, webpage_name, har_config, relays, log_file=None, num_relays=3):
        super().__init__(ndn_host, server_prefix, webpage_name, har_config, log_file)
        self.relays = relays
        self.num_relays = num_relays
        self.configure_relays()

    def configure_relays(self):

        for relay in self.relays:
            share_symmetric_key(self.ndn_host, relay, verbose=True)

    def ndn_handler(self, route):

        chosen_relays = random.sample(self.relays, self.num_relays)
        resource_path = self.match_url(route.request.url)

        if resource_path is not None:
            print(f"Trying to get {resource_path.name} over ANDaNA")
            send_andana_request(
                host = self.ndn_host,
                network_address = f"{self.server_prefix}/{resource_path.name}",
                relay_list = chosen_relays,
            )
        else:
            pass

        route.fallback()
