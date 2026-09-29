extern int fixture_dependency(void);
int fixture_root(void) { return fixture_dependency() + 1; }
