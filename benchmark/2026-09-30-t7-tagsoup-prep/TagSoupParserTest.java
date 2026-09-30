// T7 (#91/#wikipedia) unit test for org.ccil.cowan.tagsoup.Parser.setProperty/getProperty.
// Host-runnable (no boot jar needed -- Parser + org.xml.sax.* are on the JDK bootclasspath):
//   cp <walls>/bms/src/adapter/framework/mainline-stubs/java/org/ccil/cowan/tagsoup/Parser.java org/ccil/cowan/tagsoup/
//   javac org/ccil/cowan/tagsoup/Parser.java TagSoupParserTest.java && java TagSoupParserTest
// Verifies the four recognized properties round-trip and an unknown name throws SAXNotRecognizedException
// (exactly the wall wikipedia hit: NoSuchMethodError setProperty ... is now a resolvable method).
import org.ccil.cowan.tagsoup.Parser;
import org.xml.sax.SAXNotRecognizedException;

public class TagSoupParserTest {
    static int pass = 0, fail = 0;

    static void check(boolean cond, String what) {
        if (cond) { pass++; }
        else { fail++; System.out.println("FAIL: " + what); }
    }

    public static void main(String[] args) throws Exception {
        Parser p = new Parser();

        // 1. lexical-handler round-trips.
        Object lh = new Object();
        p.setProperty(Parser.lexicalHandlerProperty, lh);
        check(p.getProperty(Parser.lexicalHandlerProperty) == lh, "lexicalHandler round-trip");

        // 2. scanner / schema / auto-detector round-trip.
        Object sc = new Object(), sch = new Object(), ad = new Object();
        p.setProperty(Parser.scannerProperty, sc);
        p.setProperty(Parser.schemaProperty, sch);
        p.setProperty(Parser.autoDetectorProperty, ad);
        check(p.getProperty(Parser.scannerProperty) == sc, "scanner round-trip");
        check(p.getProperty(Parser.schemaProperty) == sch, "schema round-trip");
        check(p.getProperty(Parser.autoDetectorProperty) == ad, "autoDetector round-trip");

        // 3. null value is allowed (upstream permits clearing a handler).
        p.setProperty(Parser.lexicalHandlerProperty, null);
        check(p.getProperty(Parser.lexicalHandlerProperty) == null, "null value allowed");

        // 4. unknown property name -> SAXNotRecognizedException (not NoSuchMethodError).
        boolean threw = false;
        try { p.setProperty("http://example.com/unknown", new Object()); }
        catch (SAXNotRecognizedException e) { threw = true; }
        check(threw, "unknown setProperty throws SAXNotRecognizedException");

        threw = false;
        try { p.getProperty("http://example.com/unknown"); }
        catch (SAXNotRecognizedException e) { threw = true; }
        check(threw, "unknown getProperty throws SAXNotRecognizedException");

        System.out.println("TagSoupParserTest: " + pass + " passed, " + fail + " failed");
        if (fail != 0) System.exit(1);
    }
}
