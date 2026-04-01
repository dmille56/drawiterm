# :NOTE: this contains common dependencies
{ pkgs }:

{
  # dependencies needed during build time (include pytest so the interpreter
  # created by withPackages can run "python -m pytest")
  myBuildPackages = [
    (pkgs.python3.withPackages (ps: [
      ps.textual
      ps.rich
      ps.pytest

      ps.build
      ps.twine
    ]))
  ];
  
  # dependencies only needed for development (pytest moved into myBuildPackages)
  myDevPackages = [
    pkgs.python3Packages.coverage
    pkgs.python3Packages.ipdb
    pkgs.python3Packages.pytest-cov

    pkgs.ruff
    pkgs.ty
    pkgs.pre-commit
  ];
}
