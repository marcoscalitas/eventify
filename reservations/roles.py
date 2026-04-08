from rolepermissions.roles import AbstractUserRole


class Attendee(AbstractUserRole):
    available_permissions = {
        "reserve_event": True,
        "review_event": True,
        "favorite_event": True,
    }


class Organizer(AbstractUserRole):
    available_permissions = {
        "reserve_event": True,
        "review_event": True,
        "favorite_event": True,
        "create_event": True,
        "edit_event": True,
        "delete_event": True,
        "export_attendees": True,
    }
