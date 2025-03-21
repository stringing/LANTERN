from middleware.coordinator import Coordinator
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="config/tr.yaml",
        help="Path to the config file.",
    )
    parser.add_argument(
        '--restart', 
        default=False, 
        action=argparse.BooleanOptionalAction, 
        help="True: restart the process from the beginning. False: resume from the latest state."
    )
    args = parser.parse_args()

    cd = Coordinator(args.config, args.restart)
    cd.run()

