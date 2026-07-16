import os
import sys
import argparse
from datetime import datetime

from chronos.core.checkpoint import init_chronos, create_checkpoint
from chronos.core.status import render_status
from chronos.core.timeline import render_timeline
from chronos.core.diff import render_diff
from chronos.core.restore import plan_restore, restore_checkpoint

def main():
    parser = argparse.ArgumentParser(
        description="🔥 Phoenix Chronos - The Open-Source Checkpoint & Replay Engine for Developers",
        formatter_class=argparse.RawTextHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    subparsers.add_parser("init", help="Initialize a new empty Chronos repository in the current directory")

    # checkpoint
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Save a snapshot of your development state")
    checkpoint_parser.add_argument("-m", "--message", required=True, help="Description of the checkpoint state")

    # status
    subparsers.add_parser("status", help="Show the current status compared to the latest checkpoint")

    # timeline
    subparsers.add_parser("timeline", help="Browse checkpoints and development history")

    # diff
    diff_parser = subparsers.add_parser("diff", help="See what changed between two checkpoints")
    diff_parser.add_argument("checkpoint1", help="ID of the first checkpoint (A)")
    diff_parser.add_argument("checkpoint2", help="ID of the second checkpoint (B)")

    # restore
    restore_parser = subparsers.add_parser("restore", help="Restore the development environment to a previous checkpoint")
    restore_parser.add_argument("checkpoint", help="Checkpoint ID to restore to, or 'latest'")
    restore_parser.add_argument("--dry-run", action="store_true", help="Perform a dry run and output the restore plan without modifying files")

    args = parser.parse_args()

    root_dir = os.getcwd()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "init":
            msg = init_chronos(root_dir)
            print(f"\033[92m{msg}\033[0m")

        elif args.command == "checkpoint":
            cp_id = create_checkpoint(root_dir, args.message)
            print(f"\033[92mSuccessfully created checkpoint: {cp_id}\033[0m")

        elif args.command == "status":
            output = render_status(root_dir)
            print(output)

        elif args.command == "timeline":
            output = render_timeline(root_dir)
            print(output)

        elif args.command == "diff":
            output = render_diff(root_dir, args.checkpoint1, args.checkpoint2)
            print(output)

        elif args.command == "restore":
            plan = plan_restore(root_dir, args.checkpoint)

            # Print Restore Plan Details
            print("\n📋 \033[95mPHOENIX CHRONOS RESTORE PLAN\033[0m")
            print("================================")
            print(f"Target Checkpoint: \033[94m{plan['checkpoint']['id']}\033[0m")
            print(f"Message:           \"{plan['checkpoint']['message']}\"")
            print(f"Timestamp:         {plan['checkpoint']['timestamp']}")
            print("--------------------------------")

            if plan["files_to_restore"] or plan["files_to_delete"]:
                print("\n📁 Files to update:")
                for f, action in plan["files_to_restore"]:
                    action_color = "\033[93m" if action == "modified" else "\033[92m"
                    print(f"  {action_color}[{action.capitalize()}]\033[0m {f}")
                for f in plan["files_to_delete"]:
                    print(f"  \033[91m[Delete]\033[0m   {f}")
            else:
                print("\n📁 Files: No file changes required (local matches checkpoint).")

            if plan["packages_to_align"]:
                print("\n📦 Package Alignment Actions Required:")
                for pkg in plan["packages_to_align"]:
                    if pkg["action"] == "install":
                        print(f"  \033[92m[Install]\033[0m {pkg['manager']}: {pkg['name']}=={pkg['version']}")
                    else:
                        print(f"  \033[93m[Align]\033[0m   {pkg['manager']}: {pkg['name']} ({pkg['current_version']} -> {pkg['version']})")
            else:
                print("\n📦 Packages: Already aligned with checkpoint.")

            if plan["env_to_align"]:
                print("\n⚙️ Environment Variables Alignment Required:")
                for env in plan["env_to_align"]:
                    if env["action"] == "set":
                        print(f"  \033[92m[Set]\033[0m    {env['name']}={env['value']}")
                    else:
                        print(f"  \033[93m[Update]\033[0m {env['name']} ({env['current_value']} -> {env['value']})")
            else:
                print("\n⚙️ Environment: Already aligned with checkpoint.")

            print("")

            if args.dry_run:
                print("\033[93mDry-run mode. Workspace was NOT modified.\033[0m")
            else:
                resolved_id = restore_checkpoint(root_dir, args.checkpoint)
                print(f"\033[92mSuccessfully restored workspace files to checkpoint: {resolved_id}\033[0m")
                if plan["packages_to_align"] or plan["env_to_align"]:
                    print("\033[93mPlease align your system packages and environment variables as printed above.\033[0m")

    except Exception as e:
        print(f"\033[91mError: {e}\033[0m", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
