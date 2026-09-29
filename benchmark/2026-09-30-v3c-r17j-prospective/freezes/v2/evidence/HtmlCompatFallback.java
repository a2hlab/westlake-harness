/* r17b (#tagsoup): a tagsoup-free Html.fromHtml replacement for the Wikipedia line. */
package adapter.compat;

import android.graphics.Typeface;
import android.text.Html;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.style.StyleSpan;

/**
 * B8 (#tagsoup/r17b): route-A's BOOTCLASSPATH framework.jar ships a 9-line org.ccil.cowan.tagsoup
 * Parser stub (BCP-first wins over the runtime JAR), so android.text.Html.fromHtml dies with
 * NoSuchMethodError setProperty on the stubbed Parser (Wikipedia LanguageUtil.fromHtml -> ForYouCard).
 * Westlake has no real tagsoup either; it survives because its Html.fromHtml never reaches tagsoup.
 *
 * oc-t4's libwestlake_html_compat.so re-registers Html.fromHtml as a JNI method that calls back into
 * this class (class name from the WESTLAKE_HTML_COMPAT_CLASS env). We turn the HTML fragment into
 * displayable text with the minimum inline styling Wikipedia's first screen needs, and NEVER touch
 * org.ccil.cowan.tagsoup: b/strong -> bold, i/em -> italic, br and block tags -> newline, a -> its
 * text kept, all other tags stripped, and the standard XML/numeric entities decoded.
 *
 * Two overloads are published so the native side binds whichever descriptor it looks up: the 4-arg
 * Spanned form (matching android.text.Html.fromHtml(String,int,ImageGetter,TagHandler)) and a 2-arg
 * String form. ImageGetter/TagHandler are accepted for signature compatibility and ignored (no images
 * or custom tags on the first screen).
 */
public final class HtmlCompatFallback {
    private HtmlCompatFallback() {}

    public static Spanned fromHtmlCompat(String source, int flags, Html.ImageGetter ig, Html.TagHandler th) {
        return parse(source);
    }

    public static String fromHtmlCompat(String source, int flags) {
        return parse(source).toString();
    }

    private static Spanned parse(String source) {
        SpannableStringBuilder out = new SpannableStringBuilder();
        if (source == null) return out;
        int boldStart = -1;
        int italicStart = -1;
        int i = 0;
        int n = source.length();
        boolean lastWasNewline = true;   // suppress leading blank lines
        while (i < n) {
            char c = source.charAt(i);
            if (c == '<') {
                int end = source.indexOf('>', i + 1);
                if (end < 0) {                       // stray '<' with no '>': keep literally
                    appendChar(out, '<');
                    lastWasNewline = false;
                    i++;
                    continue;
                }
                String tag = source.substring(i + 1, end).trim();
                i = end + 1;
                boolean close = tag.startsWith("/");
                String nameTag = tagName(close ? tag.substring(1) : tag);
                if (nameTag.equals("b") || nameTag.equals("strong")) {
                    if (close) boldStart = closeSpan(out, boldStart, Typeface.BOLD);
                    else boldStart = out.length();
                } else if (nameTag.equals("i") || nameTag.equals("em")) {
                    if (close) italicStart = closeSpan(out, italicStart, Typeface.ITALIC);
                    else italicStart = out.length();
                } else if (nameTag.equals("br")) {
                    appendNewline(out, lastWasNewline);
                    lastWasNewline = true;
                } else if (nameTag.equals("p") || nameTag.equals("div") || nameTag.equals("li")
                        || nameTag.equals("tr") || nameTag.equals("h1") || nameTag.equals("h2")
                        || nameTag.equals("h3") || nameTag.equals("h4") || nameTag.equals("ul")
                        || nameTag.equals("ol") || nameTag.equals("blockquote")) {
                    appendNewline(out, lastWasNewline);
                    lastWasNewline = true;
                }
                // a, span, and every other tag: drop the tag, keep the text between them.
            } else if (c == '&') {
                int semi = source.indexOf(';', i + 1);
                if (semi > i && semi - i <= 12) {
                    String ent = source.substring(i + 1, semi);
                    String decoded = decodeEntity(ent);
                    if (decoded != null) {
                        out.append(decoded);
                        lastWasNewline = decoded.length() == 0 || decoded.charAt(decoded.length() - 1) == '\n';
                        i = semi + 1;
                        continue;
                    }
                }
                appendChar(out, '&');
                lastWasNewline = false;
                i++;
            } else if (c == '\n' || c == '\r' || c == '\t') {
                // Collapse HTML source whitespace to a single space unless we just broke a line.
                if (!lastWasNewline && out.length() > 0 && out.charAt(out.length() - 1) != ' ') {
                    out.append(' ');
                }
                i++;
            } else {
                appendChar(out, c);
                lastWasNewline = false;
                i++;
            }
        }
        // Close any span left open by malformed markup.
        if (boldStart >= 0) closeSpan(out, boldStart, Typeface.BOLD);
        if (italicStart >= 0) closeSpan(out, italicStart, Typeface.ITALIC);
        // Trim a single trailing newline the block tags may have added.
        int len = out.length();
        if (len > 0 && out.charAt(len - 1) == '\n') out.delete(len - 1, len);
        return out;
    }

    private static void appendChar(SpannableStringBuilder out, char c) {
        out.append(c);
    }

    private static void appendNewline(SpannableStringBuilder out, boolean lastWasNewline) {
        if (!lastWasNewline && out.length() > 0) out.append('\n');
    }

    /** Apply a StyleSpan from start to the current end, if the range is non-empty. Returns -1. */
    private static int closeSpan(SpannableStringBuilder out, int start, int style) {
        if (start >= 0 && out.length() > start) {
            out.setSpan(new StyleSpan(style), start, out.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        return -1;
    }

    /** Lower-cased tag name up to the first whitespace or '/', e.g. "<a href=..>" -> "a". */
    private static String tagName(String tag) {
        int cut = tag.length();
        for (int k = 0; k < tag.length(); k++) {
            char c = tag.charAt(k);
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '/') { cut = k; break; }
        }
        return tag.substring(0, cut).toLowerCase(java.util.Locale.ROOT);
    }

    /** Decode a single entity body (without & and ;). Returns null when it is not a known entity. */
    private static String decodeEntity(String ent) {
        if (ent.isEmpty()) return null;
        if (ent.charAt(0) == '#') {
            try {
                int code;
                if (ent.length() > 1 && (ent.charAt(1) == 'x' || ent.charAt(1) == 'X')) {
                    code = Integer.parseInt(ent.substring(2), 16);
                } else {
                    code = Integer.parseInt(ent.substring(1));
                }
                if (code <= 0 || code > 0x10FFFF) return null;
                return new String(Character.toChars(code));
            } catch (RuntimeException e) {
                return null;
            }
        }
        switch (ent) {
            case "amp":  return "&";
            case "lt":   return "<";
            case "gt":   return ">";
            case "quot": return "\"";
            case "apos": return "'";
            case "nbsp": return " ";
            default:     return null;
        }
    }
}
