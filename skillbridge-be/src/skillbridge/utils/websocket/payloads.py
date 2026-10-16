# Incoming message types (from client)
TYPE_SEND_MESSAGE = "send_message"  # Send a new chat message
TYPE_FETCH_HISTORY = "fetch_history"  # Load older messages in a room
TYPE_MARK_READ = "mark_read"  # Mark messages as read
TYPE_TYPING = "typing"  # User is typing indicator

# Outgoing event types (from server)
EVENT_NEW_MESSAGE = "new_message"  # A new message arrived
EVENT_HISTORY = "history"  # Response to fetch_history
EVENT_READ_RECEIPT = "read_receipt"  # Someone read your message
EVENT_TYPING = "typing"  # Someone is typing
EVENT_NOTIFICATION = "notification"  # A persisted in-app notification
EVENT_ERROR = "error"  # Something went wrong
