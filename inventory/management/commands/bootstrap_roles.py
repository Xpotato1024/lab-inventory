from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError


ROLE_PERMISSIONS = {
    "Viewer": set(),
    "Editor": {
        "add_stock",
        "change_stock",
        "change_placement",
    },
    "Maintainer": {
        "add_room",
        "change_room",
        "delete_room",
        "view_room",
        "add_fixture",
        "change_fixture",
        "delete_fixture",
        "view_fixture",
        "add_placementzone",
        "change_placementzone",
        "delete_placementzone",
        "view_placementzone",
        "add_catalogitem",
        "change_catalogitem",
        "delete_catalogitem",
        "view_catalogitem",
        "add_physicalunit",
        "change_physicalunit",
        "delete_physicalunit",
        "view_physicalunit",
        "add_stock",
        "change_stock",
        "view_stock",
        "change_placement",
        "view_placement",
        "view_stockchange",
        "view_placementchange",
    },
}


class Command(BaseCommand):
    help = "Create/update standard lab-inventory authorization groups idempotently."

    def handle(self, *args, **options):
        inventory_permissions = Permission.objects.filter(content_type__app_label="inventory")
        by_codename = {permission.codename: permission for permission in inventory_permissions}

        required = set().union(*ROLE_PERMISSIONS.values())
        missing = sorted(required - by_codename.keys())
        if missing:
            raise CommandError(f"Missing expected inventory permissions: {', '.join(missing)}")

        for role, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            group.permissions.set([by_codename[codename] for codename in sorted(codenames)])
            self.stdout.write(f"{role}: {len(codenames)} permission(s)")

        self.stdout.write(self.style.SUCCESS("Standard roles are configured."))
