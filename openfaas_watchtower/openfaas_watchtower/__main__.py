"""Main module"""

from openfaas_watchtower.watchtower import run_hey_thread, run_fetch_thread


def main():
    """Main function of the module"""
    run_hey_thread()
    run_fetch_thread()


if __name__ == "__main__":
    main()
