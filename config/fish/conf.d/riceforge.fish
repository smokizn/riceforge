# riceforge: load the active theme's fish layer (prompt, colours), if it has one.
# Themes without fish/theme.fish get stock fish. Delete this file to detach.
status is-interactive; or return
set -l __rf_fish ~/.config/riceforge/current/fish/theme.fish
test -r $__rf_fish; and source $__rf_fish
