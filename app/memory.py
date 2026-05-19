class Memory:

    def __init__(self):
        self.storage = {}

    def add_message(self, user_id, role, content):

        if user_id not in self.storage:
            self.storage[user_id] = []

        self.storage[user_id].append({
            "role": role,
            "content": content
        })

    def get_history(self, user_id):

        return self.storage.get(user_id, [])