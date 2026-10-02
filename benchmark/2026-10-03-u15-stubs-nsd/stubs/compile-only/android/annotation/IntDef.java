package android.annotation;

import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import static java.lang.annotation.ElementType.ANNOTATION_TYPE;

/** COMPILE-ONLY stand-in for AOSP's hidden android.annotation.IntDef (SOURCE retention; never enters the dex). */
@Retention(RetentionPolicy.SOURCE)
@Target({ANNOTATION_TYPE})
public @interface IntDef {
    String[] prefix() default {};
    String[] suffix() default {};
    int[] value() default {};
    boolean flag() default false;
}
