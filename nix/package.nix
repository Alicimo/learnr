{
  lib,
  python313Packages,
}:

python313Packages.buildPythonPackage {
  pname = "learnr";
  version = "0.1.0";
  pyproject = true;

  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [
      ../learnr
      ../tests
      ../pyproject.toml
      ../README.md
    ];
  };

  build-system = with python313Packages; [
    hatchling
  ];

  dependencies = with python313Packages; [
    fastapi
    pydantic-settings
    python-multipart
    sqlalchemy
    uvicorn
  ];

  nativeCheckInputs = with python313Packages; [
    httpx
    pytest
  ];

  pythonImportsCheck = [
    "learnr.main"
  ];

  checkPhase = ''
    runHook preCheck
    pytest
    runHook postCheck
  '';

  meta = {
    description = "Swipe-based spaced repetition vocabulary trainer";
    mainProgram = "learnr";
    platforms = lib.platforms.unix;
  };
}
