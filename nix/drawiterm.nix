{ pkgs }:

let 
  common = import ./common.nix { inherit pkgs; };
in
pkgs.python3Packages.buildPythonPackage rec {
  pname = "drawiterm";
  version = "0.1.4";
 
  # source: use the current directory
  src = ../.;
  
  pyproject = true;

  # python dependencies from nixpkgs (if available)
  propagatedBuildInputs = common.myBuildPackages;

  # if you need system libs or build tools:
  nativeBuildInputs = [ 
    pkgs.python3Packages.setuptools
    pkgs.python3Packages.wheel
  ];

  # optional metadata
  meta = with pkgs.lib; {
    description = "drawiterm";
    license = licenses.mit;
  };
}
