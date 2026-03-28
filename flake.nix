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
          '';
        };
        
        packages.default = import ./nix/drawiterm.nix { inherit pkgs; };
      };

      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
    };
}
