# learnr

Swipe-based vocabulary review with a Python/FastAPI backend and SQLite storage.

## Run

```bash
uv sync
uv run uvicorn learnr.main:app --reload
```

Then open <http://127.0.0.1:8000>.

By default the SQLite database is created at `./learnr.sqlite3`. Override it with:

```bash
LEARNR_DB_PATH=/path/to/learnr.sqlite3 uv run uvicorn learnr.main:app --reload
```

On first startup with an empty database, learnr automatically imports the bundled
Goethe A1 starter deck so a fresh deployment has review cards immediately.

## NixOS Deployment

This repository exposes a flake package and a NixOS module. A server flake can
target the GitHub repository directly:

```nix
{
  inputs.learnr.url = "github:your-user/learnr";

  outputs =
    { nixpkgs, learnr, ... }:
    {
      nixosConfigurations.server = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          learnr.nixosModules.default
          {
            services.learnr = {
              enable = true;
              host = "127.0.0.1";
              port = 8000;
              databasePath = "/var/lib/learnr/learnr.sqlite3";
            };
          }
        ];
      };
    };
}
```

The module only manages the application service. Configure TLS, reverse proxying,
firewall rules, and backups in the server configuration.

## Scheduler Settings

The v0 scheduler is a simple binary placeholder, not a full Anki/FSRS implementation. Its tuning values can be overridden with environment variables using the `LEARNR_SCHEDULER_` prefix, for example:

```bash
LEARNR_SCHEDULER_AGAIN_INTERVAL_MINUTES=5 uv run uvicorn learnr.main:app --reload
```

## CSV Import

The importer accepts:

```csv
front,back,deck,tags,source_language,target_language
Apfel,apple,German A1,noun;food,de,en
Buch,book,German A1,noun,de,en
```

Required columns are `front` and `back`. `deck`, `tags`, `source_language`, and `target_language` are optional. Every row creates or reuses a note and generates forward and reverse cards. Cards are deduplicated and can belong to multiple decks.

The bundled Goethe A1 CSV is based on the Goethe-Institut A1 word list, with English translations adapted from `patsytau/anki_german_a1_vocab` under CC BY-SA 4.0.
