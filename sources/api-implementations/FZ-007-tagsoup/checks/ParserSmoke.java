import java.io.StringReader;
import org.ccil.cowan.tagsoup.Parser;
import org.xml.sax.InputSource;
import org.xml.sax.XMLReader;
import org.xml.sax.helpers.DefaultHandler;
public final class ParserSmoke {
    public static void main(String[] args) throws Exception {
        XMLReader parser = new Parser();
        final StringBuilder text = new StringBuilder();
        final int[] elements = {0};
        parser.setContentHandler(new DefaultHandler() {
            public void startElement(String uri, String local, String name, org.xml.sax.Attributes attrs) { elements[0]++; }
            public void characters(char[] chars, int start, int length) { text.append(chars, start, length); }
        });
        parser.parse(new InputSource(new StringReader("<html><body><p>Hello &amp; <b>world<p>Next")));
        if (!text.toString().equals("Hello & worldNext") || elements[0] < 5) {
            throw new AssertionError("Malformed HTML / entity SAX parse failed: " + text);
        }
        System.out.println("PASS XMLReader assignment, malformed HTML repair, entity decoding, SAX callbacks; elements=" + elements[0]);
    }
}
