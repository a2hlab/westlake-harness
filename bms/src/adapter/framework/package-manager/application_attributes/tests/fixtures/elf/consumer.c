extern int fixture_dependency(void);
int fixture_export(void) { return fixture_dependency() + 1; }
