from imdb_repository import ImdbRepository
from linker import get_default_mapper


def total_runtime(tids: list[str]) -> int:
    repo = ImdbRepository()
    runtimes = repo.find_runtimes_by_tids(tids)
    return sum(runtimes.values())


if __name__ == "__main__":
    mapper = get_default_mapper()
    journal = mapper.load_journal()

    tids = [j.tid for j in journal if j.tid]
    total = total_runtime(tids)

    hours = total // 60
    days = hours // 24

    print(f"Total runtime: {total:,} minutes")
    print(f"= ~{hours:,} hours (~{days:,} days)")
