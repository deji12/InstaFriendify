from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, BadPassword, 
    BadCredentials, TwoFactorRequired, 
    UnknownError
)
import time
import os
import logging
from dataclasses import dataclass, asdict
import random
from hikerapi import Client as HikerClient
import json
from decouple import config

from Core.utils import (
    VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT,
    TWO_FACTOR_REQUIRED_FOR_ACCOUNT,
    UNKNOWN_ERROR,
    INVALID_CREDENTIALS
)

# COLOR FORMATS
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

@dataclass
class BotConfig:
    """
    Configuration class for the Instagram bot.
    Attributes:
        followers_batch_size (int): Number of followers to process in a single batch.
        batch_cooldown (int): Cooldown time between batches in seconds.
        max_followers (int): Maximum number of followers to fetch.
        action_delay_min (int): Minimum delay between actions in seconds.
        action_delay_max (int): Maximum delay between actions in seconds.
    """
    followers_batch_size: int = 200
    batch_cooldown: int = 60
    max_followers: int = 100  # Default value
    action_delay_min: int = 2  # Minimum delay between actions
    action_delay_max: int = 5  # Maximum delay between actions

class InstagramChallengeRequired(Exception):
    """Exception raised when Instagram requires a verification code"""
    pass

class InstagramBot:
    """
    A bot to automate interactions with Instagram, such as fetching followers and adding them to close friends.
    Attributes:
        user (str): The username of the bot operator.
        base_data_dir (str): Base directory for storing user data.
        hiker_token (str): Token for the Hiker API.
        accounts_dir (str): Directory to store account data.
        followers_path (str): Directory to store followers data.
        last_added_path (str): Directory to store the last added follower.
        cache_path (str): Directory to store session cache.
        accounts (dict): Dictionary to store account details.
    """
    def __init__(self, user=None):

        self.user = user
        self.base_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../users'))
        self.hiker_token = config('HIKER_TOKEN')

        if self.user is not None:
            self.accounts_dir = os.path.join(self.base_data_dir, f'{self.user}/accounts')

            self.accounts = self._load_accounts()

            self.followers_path = os.path.join(self.base_data_dir, f'{self.user}/followers')
            self.last_added_path = os.path.join(self.base_data_dir, f'{self.user}/last_added')
            self.cache_path = os.path.join(self.base_data_dir, f'{self.user}/cache')
        
        self._setup_logging()

    def _setup_directories(self, user) -> None:
        """Create necessary directories for the user."""

        self.user_account = os.path.join(self.base_data_dir, f'{user}')
        os.makedirs(self.user_account, exist_ok=True)

        for subdir in ['accounts', 'cache', 'followers', 'last_added']:
            path = os.path.join(self.user_account, subdir)
            os.makedirs(path, exist_ok=True)

    def _setup_logging(self):
        """Configure logging for the bot."""

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=f'{self.base_data_dir}/bot.log'
        )

    def _load_accounts(self):
        """Load account data from JSON files."""

        accounts = {}
        if os.path.exists(self.accounts_dir):
            for filename in os.listdir(self.accounts_dir):
                if filename.endswith('.json'):
                    username = filename[:-5]  # Remove '.json'
                    with open(os.path.join(self.accounts_dir, filename), 'r') as f:
                        accounts[username] = json.load(f)
        return accounts
    
    def _get_account(self, username):
        """Retrieve account details for a given username."""

        account_data = self.accounts[username]
        config = BotConfig(**account_data['config'])

        return username, account_data['password'], config

    def _account_exists(self, account):
        """Check if an account directory exists."""

        return os.path.exists(f'{self.base_data_dir}/{account}')
    
    def _ig_account_exists(self, username):
        """Check if an Instagram account JSON file exists."""

        return os.path.exists(f'{self.accounts_dir}/{username}.json')

    def custom_code_handler(self, username, choice=None):
        """Handle Instagram verification code requests."""

        if self.verification_code is not None:
            return self.verification_code
        else:
            raise InstagramChallengeRequired(f"Challenge required for {username} via {choice}")

    def create_new_account(self, username, password, max_followers, verification_code=None, two_factor_verification_code=None):
        
        """Add a new Instagram account and save its details."""

        logging.info(f"🤖 -> {HEADER}Received Instagram username & password{ENDC}")

        self.verification_code = verification_code

        if self._account_exists(username):
            return False, "An account with that username already exists"

        # Create a temporary client to test login
        temp_client = Client()
        temp_client.challenge_code_handler = self.custom_code_handler
        try:
            if not temp_client.login(
                username = username, 
                password = password, 
                verification_code = two_factor_verification_code if two_factor_verification_code is not None else ''
            ):
                return False, INVALID_CREDENTIALS
            else:
                self._setup_directories(self.user)
                cache_path = f'{self.user_account}/cache/{username}_session.json'
                temp_client.dump_settings(cache_path)

        except InstagramChallengeRequired as e:
            return False, VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT
        
        except TwoFactorRequired as e:
            return False, TWO_FACTOR_REQUIRED_FOR_ACCOUNT
        
        except UnknownError as e:
            return False, UNKNOWN_ERROR
        
        except BadPassword as e:
            return False, INVALID_CREDENTIALS
        
        except BadCredentials as e:
            return False, INVALID_CREDENTIALS

        # Save the account data only if login is successful
        config = BotConfig(max_followers=max_followers)
        account_data = {
            'username': username,
            'password': password,
            'config': asdict(config),
            'adding_to_close_friends': False,
            'getting_followers': False,
        }

        # Save user's account details
        with open(os.path.join(self.user_account, f'accounts/{username}.json'), 'w') as f:
            json.dump(account_data, f)

        from Core.models import User

        user = User.objects.get(username=self.user)
        user.current_allocation += max_followers
        user.save()

        return True, "Account connected successfully"
    
    def get_user_accounts(self):
        """Retrieve a list of all user accounts."""

        accounts = []
        if self._account_exists(self.user):
            for filename in os.listdir(self.accounts_dir):
                if filename.endswith('.json'):
                    username = filename[:-5]  # Remove '.json'
                    with open(os.path.join(f'{self.base_data_dir}/{self.user}/accounts', filename), 'r') as f:
                        account_data = json.load(f)
                        followers_count = account_data.get('followers_count', 0)
                        adding_to_close_friends = account_data.get('adding_to_close_friends', False)
                        getting_followers = account_data.get('getting_followers', False)
                        accounts.append({
                            'username': username,
                            'followers_count': followers_count,
                            'adding_to_close_friends': adding_to_close_friends,
                            'getting_followers': getting_followers
                        })
        return accounts
    
    def _rename_account_files(self, old_username, new_username):
        """Rename all files associated with an account when the username changes."""
    
        try:
            # Rename account file
            old_account_file = os.path.join(self.accounts_dir, f'{old_username}.json')
            new_account_file = os.path.join(self.accounts_dir, f'{new_username}.json')
            if os.path.exists(old_account_file):
                os.rename(old_account_file, new_account_file)

            # Rename followers file
            old_followers_file = os.path.join(self.followers_path, f'{old_username}.txt')
            new_followers_file = os.path.join(self.followers_path, f'{new_username}.txt')
            if os.path.exists(old_followers_file):
                os.rename(old_followers_file, new_followers_file)

            # Rename last_added file
            old_last_added_file = os.path.join(self.last_added_path, f'{old_username}.txt')
            new_last_added_file = os.path.join(self.last_added_path, f'{new_username}.txt')
            if os.path.exists(old_last_added_file):
                os.rename(old_last_added_file, new_last_added_file)

            # Rename cache file
            old_cache_file = os.path.join(self.cache_path, f'{old_username}_session.json')
            new_cache_file = os.path.join(self.cache_path, f'{new_username}_session.json')
            if os.path.exists(old_cache_file):
                os.rename(old_cache_file, new_cache_file)

            logging.info(f"Renamed files for account '{old_username}' to '{new_username}'.")
        except Exception as e:
            logging.error(f"Failed to rename files for account '{old_username}': {e}")

    def update_ig_account(
            self, old_username, 
            username = None, 
            password = None, 
            number_of_followers = None, 
            verification_code=None,
            two_factor_verification_code=None
        ):

        """Update an existing Instagram account's details."""

        self.verification_code = verification_code
    
        account_file = os.path.join(self.accounts_dir, f'{old_username}.json')
        
        if not os.path.exists(account_file):
            return False, f"Account '{old_username}' does not exist."

        try:
            # Load the existing account data
            with open(account_file, 'r') as f:
                account_data = json.load(f)

            # Validate credentials if username or password is being updated
            if account_data["username"] != username or account_data["password"] != password:
                temp_client = Client()
                temp_client.challenge_code_handler = self.custom_code_handle
                try:
                    if not temp_client.login(
                        username = username or old_username, 
                        password = password or account_data['password'],
                        verification_code = two_factor_verification_code if two_factor_verification_code is not None else ''
                    ):
                        return False, "Invalid credentials provided."
                    
                    # Save the new session if credentials are valid
                    cache_path = f'{self.user_account}/cache/{username or old_username}_session.json'
                    temp_client.dump_settings(cache_path)
                
                except InstagramChallengeRequired as e:
                    return False, VERIFICATION_CODE_REQUIRED_FOR_ACCOUNT
                
                except TwoFactorRequired as e:
                    return False, TWO_FACTOR_REQUIRED_FOR_ACCOUNT
                
                except UnknownError as e:
                    return False, UNKNOWN_ERROR
                
                except BadPassword as e:
                    return False, INVALID_CREDENTIALS
                
                except BadCredentials as e:
                    return False, INVALID_CREDENTIALS

            # Update username if provided
            if account_data["username"] != username:
                # Rename all associated files
                self._rename_account_files(old_username, username)
                account_data['username'] = username

            # Update password if provided
            if password:
                account_data['password'] = password

            # Update number_of_followers if provided
            if number_of_followers is not None:
                account_data['config']['max_followers'] = number_of_followers

            # Save the updated account data back to the file
            new_account_file = os.path.join(self.accounts_dir, f'{username or old_username}.json')
            with open(new_account_file, 'w') as f:
                json.dump(account_data, f)

            logging.info(f"Account '{username or old_username}' updated successfully.")
            return True, f"Account '{username or old_username}' updated successfully."

        except Exception as e:
            logging.error(f"Failed to update account '{old_username}': {e}")
            return False, f"Failed to update account '{old_username}'."
        
    def update_adding_to_close_friends_status(self, username, status):
       
        account_file = os.path.join(self.accounts_dir, f'{username}.json')
        if os.path.exists(account_file):
            with open(account_file, 'r') as f:
                account_data = json.load(f)
            account_data['adding_to_close_friends'] = status
            with open(account_file, 'w') as f:
                json.dump(account_data, f)

    def update_getting_followers_status(self, username, status):
       
        account_file = os.path.join(self.accounts_dir, f'{username}.json')
        if os.path.exists(account_file):
            with open(account_file, 'r') as f:
                account_data = json.load(f)
            account_data['getting_followers'] = status
            with open(account_file, 'w') as f:
                json.dump(account_data, f)
        
    def _initialize_client(self, username, add_to_close_friends_mode=False) -> Client:
        client = Client()
        client.delay_range = [1, 5]

        if add_to_close_friends_mode:
            proxy_login = config('PROXY_LOGIN')
            proxy_password = config('PROXY_PASSWORD')
            proxy_host = config('PROXY_HOST')
            proxy_port = config('PROXY_PORT')
            
            proxy_url = f"http://{proxy_login}:{proxy_password}@{proxy_host}:{proxy_port}"
            client.set_proxy(proxy_url)

        try:
            if os.path.exists(f'{self.cache_path}/{username}_session.json') and os.path.getsize(f'{self.cache_path}/{username}_session.json') > 0:
                session = client.load_settings(f'{self.cache_path}/{username}_session.json')
                if session:
                    client.set_settings(session)
                    self._validate_session(client)
            else:
                self._login_with_credentials(client)

            client.dump_settings(f'{self.cache_path}/{username}_session.json')

            self.user_id = client.user_id
            return client
            

        except BadPassword as e:
            logging.error(f"Login failed: {e}")
            logging.info(f"🤖 -> {FAIL}Incorrect username or password. Please reset the account.{ENDC}")
           
            # Delete the account's JSON file
            account_file = os.path.join(self.accounts_dir, f'{self.username}.json')
            if os.path.exists(account_file):
                os.remove(account_file)
            raise  # Re-raise the exception to stop further execution
        except Exception as e:
            logging.error(f"Failed to initialize client: {e}")
            raise

    def _initialize_credentials(self, username):
        self.username, self.password, self.config = self._get_account(username)
        self.client = self._initialize_client(username)

    def _validate_session(self, client: Client):
        try:
            client.login(self.username, self.password)
            client.get_timeline_feed()
        except LoginRequired:
            logging.warning("Session invalid, performing fresh login")
            old_settings = client.get_settings()
            client.set_settings({})
            client.set_uuids(old_settings["uuids"])
            self._login_with_credentials(client)

    def _login_with_credentials(self, client: Client):
        logging.info(f"Logging in as {self.username}")
        try:
            if not client.login(self.username, self.password):
                raise Exception("Failed to login with credentials")
        except BadPassword as e:
            logging.error(f"Login failed: {e}")
            logging.info(f"🤖 -> {FAIL}Incorrect username or password. Please try again.{ENDC}")
           
            # Delete the account's JSON file if it exists
            account_file = os.path.join(self.accounts_dir, f'{self.username}.json')
            if os.path.exists(account_file):
                os.remove(account_file)
            raise  # Re-raise the exception to stop further execution

    def initialise_scrape_followers_task(self, username):
        if os.path.exists(f'{self.followers_path}/{username}.txt') and os.path.getsize(f'{self.followers_path}/{username}.txt') > 0:
            return False, f"Followers already scraped for {username}. To get followers again, reset this account's followers."
        
        from Core.tasks import get_account_followers
        
        get_account_followers.delay(user=self.user, username=username)
        return True, f"We have started gathering followers for {username}."
        
    def get_followers_via_hiker(self, username):
        self._initialize_credentials(username)
        hiker_client = HikerClient(token=self.hiker_token)
        
        followers = []
        
        self.update_getting_followers_status(username, True)
        next_page_id = None

        while len(followers) < self.config.max_followers:
        
            get_followers = hiker_client.user_followers_v2(user_id=self.user_id, page_id=next_page_id)

            for follower in get_followers["response"]["users"]:
                followers.append(follower)
            
            next_page_id = get_followers["next_page_id"]
        
        followers_list = followers[:self.config.max_followers]
        
        self._save_followers_from_hiker(followers_list)
        self.update_getting_followers_status(username, False)

    def _save_followers_from_hiker(self, followers):
        
        followers_count = len(followers)
        with open(f'{self.followers_path}/{self.username}.txt', 'w') as f:
            for follower in followers:
                f.write(f"{follower.get('id')}\n")
                logging.info(f"Saved follower: {follower.get('username')}")
                logging.info(f"🤖 -> {OKCYAN}Saved username{ENDC}: {WARNING}{follower.get('username')}{ENDC}")

        # Update the account's JSON file to include the number of followers
        account_file = os.path.join(self.accounts_dir, f'{self.username}.json')
        if os.path.exists(account_file):
            with open(account_file, 'r') as f:
                account_data = json.load(f)
            account_data['followers_count'] = followers_count
            with open(account_file, 'w') as f:
                json.dump(account_data, f)
    
    def get_followers_via_instagrapi(self, username):
        self._initialize_credentials(username)
        try:
            self.update_getting_followers_status(username, True)
            followers = self.client.user_followers(
                user_id=self.client.user_id,
                amount=self.config.max_followers
            )
            self._save_followers_from_instagrapi(followers)
            self.update_getting_followers_status(username, False)

        except Exception as e:
            self.update_getting_followers_status(username, False)
            logging.error(f"Failed to fetch followers: {e}")

    def _save_followers_from_instagrapi(self, followers):
        followers_count = len(followers)
        with open(f'{self.followers_path}/{self.username}.txt', 'w') as f:
            for uid, user in followers.items():
                f.write(f'{uid}\n')
                logging.info(f"🤖 -> {OKCYAN}Saved username{ENDC}: {WARNING}{user.username}{ENDC}")

        # Update the account's JSON file to include the number of followers
        account_file = os.path.join(self.accounts_dir, f'{self.username}.json')
        if os.path.exists(account_file):
            with open(account_file, 'r') as f:
                account_data = json.load(f)
            account_data['followers_count'] = followers_count
            with open(account_file, 'w') as f:
                json.dump(account_data, f)

    def intialize_close_friends_add(self, username):

        if not os.path.exists(f'{self.followers_path}/{username}.txt') or os.path.getsize(f'{self.followers_path}/{username}.txt') == 0: 
            return False, "No followers found. Please select 'Get followers' before you can add followers to close friends."

        from Core.tasks import add_followers_to_close_freinds
        
        add_followers_to_close_freinds.delay(user=self.user, username=username)
        return True, f"Adding followers of {username} to close friends."

    def add_to_close_friends(self, username):

        self.username, self.password, self.config = self._get_account(username)
        self.client = self._initialize_client(username, add_to_close_friends_mode=True)
        
        followers = self._read_followers(username)
        last_added = self._get_last_added(username)

        if last_added:
            last_index = followers.index(last_added)
            followers = followers[last_index + 1:]

        logging.info(f"🤖 -> {HEADER}Adding followers to Close Friends{ENDC}: {WARNING}{username}...{ENDC}")

        batch_size = self.config.followers_batch_size
        total_followers = len(followers)

        self.update_adding_to_close_friends_status(username, True)
        try:
            for i in range(0, total_followers, batch_size):
                batch = followers[i:i + batch_size]
                logging.info(f"🤖 -> {OKCYAN}Processing batch {i // batch_size + 1}/{-(-total_followers // batch_size)}{ENDC}")

                for follower in batch:
                    try:
                        self.client.close_friend_add(user_id=follower)
                        logging.info(f"Added {follower} to Close Friends\n")
                        self._save_last_added(username, follower)
                        time.sleep(random.uniform(self.config.action_delay_min, self.config.action_delay_max))
                    except Exception as e:
                        self.update_adding_to_close_friends_status(username, False)
                        logging.error(f"Failed to add {follower}: {e}")

                cooldown = random.uniform(self.config.batch_cooldown, self.config.batch_cooldown * 2)
                logging.info(f"Cooling down for {cooldown:.2f} seconds...")
                time.sleep(cooldown)

            self.update_adding_to_close_friends_status(username, False)
        except Exception as e:
            self.update_adding_to_close_friends_status(username, False)
            logging.info("Error: ", e)

    def _read_followers(self, username):
        with open(f'{self.followers_path}/{username}.txt', 'r') as f:
            return f.read().splitlines()

    def _get_last_added(self, username):
        if os.path.exists(f'{self.last_added_path}/{username}.txt'):
            with open(f'{self.last_added_path}/{username}.txt', 'r') as f:
                return f.read().strip()
        return ""

    def _save_last_added(self, username, user_id):
        with open(f'{self.last_added_path}/{username}.txt', 'w') as f:
            f.write(user_id)

    def reset_user_followers(self, username) -> None:

        self.username, self.password, self.config = self._get_account(username)
        max_followers = self.config.max_followers

        if os.path.exists(f'{self.followers_path}/{self.username}.txt'):
            os.remove(f'{self.followers_path}/{self.username}.txt')

        # removed last added incase user wants to get more followers. Script will remember where it stopped

        # if os.path.exists(f'{self.last_added_path}/{self.username}.txt'):
        #     os.remove(f'{self.last_added_path}/{self.username}.txt')

        # Update the account's JSON file to include the number of followers
        account_file = os.path.join(self.accounts_dir, f'{self.username}.json')
        if os.path.exists(account_file):
            with open(account_file, 'r') as f:
                account_data = json.load(f)
            account_data['followers_count'] = 0
            with open(account_file, 'w') as f:
                json.dump(account_data, f)

        from Core.models import User

        user = User.objects.get(username=self.user)
        user.current_allocation -= max_followers
        user.save()

        return True, "Account details reset successfully"

    def delete_ig_account(self, username):

        if self._ig_account_exists(username):

            self.username, self.password, self.config = self._get_account(username)

            from Core.models import User

            user = User.objects.get(username=self.user)
            user.current_allocation -= self.config.max_followers
            user.save()

            if os.path.exists(f'{self.accounts_dir}/{username}.json'):
                os.remove(f'{self.accounts_dir}/{username}.json')

            if os.path.exists(f'{self.cache_path}/{username}_session.json'):
                os.remove(f'{self.cache_path}/{username}_session.json')

            if os.path.exists(f'{self.followers_path}/{username}.txt'):
                os.remove(f'{self.followers_path}/{username}.txt')

            if os.path.exists(f'{self.last_added_path}/{username}.txt'):
                os.remove(f'{self.last_added_path}/{username}.txt')

            return True, f"Account '{username}' deleted successfully"
        
        return False, f"No account with that username exists"