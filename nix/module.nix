{
  config,
  lib,
  pkgs,
  ...
}:

let
  cfg = config.services.learnr;
  pythonEnv = pkgs.python313.withPackages (
    ps: [
      cfg.package
      ps.uvicorn
    ]
  );
in
{
  options.services.learnr = {
    enable = lib.mkEnableOption "learnr vocabulary trainer";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ./package.nix { };
      defaultText = lib.literalExpression "pkgs.callPackage ./nix/package.nix { }";
      description = "The learnr package to run.";
    };

    host = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = "Host address uvicorn should bind to.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8000;
      description = "TCP port uvicorn should bind to.";
    };

    databasePath = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/learnr/learnr.sqlite3";
      description = "SQLite database path.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.learnr = {
      description = "learnr vocabulary trainer";
      after = [ "network.target" ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        LEARNR_DB_PATH = toString cfg.databasePath;
      };

      serviceConfig = {
        DynamicUser = true;
        StateDirectory = "learnr";
        WorkingDirectory = "/var/lib/learnr";
        ExecStart = "${pythonEnv}/bin/python -m uvicorn learnr.main:app --host ${cfg.host} --port ${toString cfg.port}";
        Restart = "on-failure";
        RestartSec = "5s";
        NoNewPrivileges = true;
        PrivateTmp = true;
      };
    };
  };
}
