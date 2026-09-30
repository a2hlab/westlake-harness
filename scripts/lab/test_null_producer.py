#!/usr/bin/env python3
"""Unit tests for null_producer.py -- the NPE null-origin classifier.

Synthetic smali methods cover each producer kind; no APK/JVM needed.
Run: python3 scripts/lab/test_null_producer.py
"""
import unittest

import null_producer as np


def method(body, name='m'):
    return f".method public {name}()V\n    .registers 6\n{body}\n.end method\n"


class ClassifyTests(unittest.TestCase):
    def analyze(self, body, npe, method_name='m', line=None):
        return np.analyze(method(body, method_name), method_name, *npe.rsplit('.', 1), line)

    def test_framework_api_returns_null(self):
        body = (
            '    const-string v1, "wifi"\n'
            '    invoke-virtual {v0, v1}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;\n'
            '    move-result-object v2\n'
            '    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
        )
        r = self.analyze(body, 'java.lang.Object.getClass')
        self.assertEqual(r['category'], 'framework')
        self.assertIn('getSystemService', r['detail'])

    def test_inherited_framework_method_on_app_subclass(self):
        # registerReceiver is called on the app's own Activity subclass, but is a framework method.
        body = (
            '    const/4 v7, 0x0\n'
            '    iget-object v10, v0, Lnet/x/DrawPreview;->f:Landroid/content/IntentFilter;\n'
            '    invoke-virtual {v6, v7, v10}, Lnet/x/MainActivity;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;)Landroid/content/Intent;\n'
            '    move-result-object v6\n'
            '    const-string v7, "level"\n'
            '    invoke-virtual {v6, v7, v10}, Landroid/content/Intent;->getIntExtra(Ljava/lang/String;I)I\n'
        )
        r = self.analyze(body, 'android.content.Intent.getIntExtra')
        self.assertEqual(r['category'], 'framework')
        self.assertIn('registerReceiver', r['detail'])

    def test_app_method_returns_null_is_app(self):
        body = (
            '    invoke-virtual {v0}, Lcom/example/App;->buildThing()Lcom/example/Thing;\n'
            '    move-result-object v2\n'
            '    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
        )
        r = self.analyze(body, 'java.lang.Object.getClass')
        self.assertEqual(r['category'], 'app')

    def test_app_field_is_app(self):
        body = (
            '    iget-object v2, v0, Lcom/example/App;->thing:Lcom/example/Thing;\n'
            '    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
        )
        r = self.analyze(body, 'java.lang.Object.getClass')
        self.assertEqual(r['category'], 'app')
        self.assertIn('field', r['detail'])

    def test_explicit_null_const_is_app(self):
        body = (
            '    const/4 v2, 0x0\n'
            '    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
        )
        r = self.analyze(body, 'java.lang.Object.getClass')
        self.assertEqual(r['category'], 'app')
        self.assertIn('null literal', r['detail'])

    def test_param_is_undeterminable(self):
        body = (
            '    invoke-virtual {p1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
        )
        r = self.analyze(body, 'java.lang.Object.getClass')
        self.assertEqual(r['category'], 'undeterminable')

    def test_line_disambiguates_multiple_targets(self):
        body = (
            '    .line 10\n'
            '    iget-object v2, v0, Lcom/example/App;->ok:Lcom/example/Thing;\n'
            '    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
            '    .line 20\n'
            '    invoke-virtual {v0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;\n'
            '    move-result-object v3\n'
            '    invoke-virtual {v3}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n'
        )
        # at line 20 the null comes from getApplicationContext (framework)
        r = self.analyze(body, 'java.lang.Object.getClass', line=20)
        self.assertEqual(r['category'], 'framework')
        self.assertIn('getApplicationContext', r['detail'])
        # at line 10 it is an app field
        r = self.analyze(body, 'java.lang.Object.getClass', line=10)
        self.assertEqual(r['category'], 'app')

    def test_move_object_alias_is_followed(self):
        body = (
            '    invoke-interface {v0, v2}, Landroid/content/RestrictionsManager;->getManifestRestrictions(Ljava/lang/String;)Ljava/util/List;\n'
            '    move-result-object v4\n'
            '    move-object v5, v4\n'
            '    invoke-interface {v5}, Ljava/util/Collection;->iterator()Ljava/util/Iterator;\n'
        )
        r = self.analyze(body, 'java.util.Collection.iterator')
        self.assertEqual(r['category'], 'framework')
        self.assertIn('getManifestRestrictions', r['detail'])

    def test_method_not_found(self):
        r = np.analyze(method('    return-void\n'), 'nope', 'java.lang.Object', 'getClass')
        self.assertIn('error', r)


if __name__ == '__main__':
    unittest.main()
