{
  description = "Swipe-based spaced repetition vocabulary trainer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];

      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        rec {
          learnr = pkgs.callPackage ./nix/package.nix { };
          default = learnr;
        }
      );

      apps = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          package = self.packages.${system}.default;
          pythonEnv = pkgs.python313.withPackages (
            ps: [
              package
              ps.uvicorn
            ]
          );
          runner = pkgs.writeShellApplication {
            name = "learnr";
            runtimeInputs = [ pythonEnv ];
            text = ''
              exec python -m uvicorn learnr.main:app "$@"
            '';
          };
        in
        {
          default = {
            type = "app";
            program = "${runner}/bin/learnr";
          };
        }
      );

      nixosModules.default = import ./nix/module.nix;
    };
}
