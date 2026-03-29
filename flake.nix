{
  # .
  description = "drawiterm flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {

      perSystem = { self', pkgs, system, ... }:
      let
        common = import ./nix/common.nix { inherit pkgs; };
      in 
      {
        devShells.default = pkgs.mkShell {
          packages = common.myBuildPackages ++ common.myDevPackages;

          shellHook = ''
            # so running the python module runs correctly
            export PYTHONPATH="src"

            # convenience helpers to run the project as a module:
            # - drawiterm: simple alias
            # - run-drawiterm: function that forwards arguments
            alias drawiterm='python -m drawiterm'
            run-drawiterm() { python -m drawiterm "$@"; }
            # export function on shells that support it (ignore errors)
            export -f run-drawiterm 2>/dev/null || true
          '';
        };
        
        packages.default = import ./nix/drawiterm.nix { inherit pkgs; };
      };

      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
    };
}
