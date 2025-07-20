# bogabot

## Description
Bogabot k8s

## Usage

### Fetch the package
`kpt pkg get REPO_URI[.git]/PKG_PATH[@VERSION] bogabot`
Details: https://kpt.dev/reference/cli/pkg/get/

### View package content
`kpt pkg tree bogabot`
Details: https://kpt.dev/reference/cli/pkg/tree/

### Apply the package
```
kpt live init bogabot
kpt live apply bogabot --reconcile-timeout=2m --output=table
```
Details: https://kpt.dev/reference/cli/live/
