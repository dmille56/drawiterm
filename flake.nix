{
  #
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
        runcommand = pkgs.writeShellScriptBin "myrun" ''
          #!${pkgs.bash}/bin/bash
          python -m drawiterm $*
        '';
        releasecommand = pkgs.writeShellScriptBin "myrelease" ''
          #!${pkgs.bash}/bin/bash
          python scripts/bump_version.py $*
        '';
      in 
      {
        devShells.default = pkgs.mkShell {
          packages = common.myBuildPackages ++ common.myDevPackages;
          buildInputs = [ runcommand releasecommand ];

          shellHook = ''
            # so running the python module runs correctly
            export PYTHONPATH="src:."
          '';
        };
        
        packages.default = import ./nix/drawiterm.nix { inherit pkgs; };
      };

      flake = {
        overlays.default = final: _prev: {
          drawiterm = import ./nix/drawiterm.nix { pkgs = final; };
        };
      };

      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
    };
}
