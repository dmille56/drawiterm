# :NOTE: this contains common dependencies
{ pkgs }:

{
  # dependencies needed during build time
  myBuildPackages = [
    pkgs.python3Packages.textual
  ];
  
  # dependencies only needed for development
  myDevPackages = [
    pkgs.python3Packages.coverage
    pkgs.python3Packages.pytest
    pkgs.python3Packages.ipdb

    pkgs.ruff
    pkgs.ty
  ];
}
