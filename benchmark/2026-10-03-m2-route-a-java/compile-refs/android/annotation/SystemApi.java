package android.annotation;
import java.lang.annotation.*;
@Retention(RetentionPolicy.SOURCE)
@Target({ElementType.TYPE,ElementType.METHOD,ElementType.PARAMETER,ElementType.FIELD,ElementType.CONSTRUCTOR,ElementType.ANNOTATION_TYPE,ElementType.PACKAGE,ElementType.LOCAL_VARIABLE,ElementType.TYPE_USE})
public @interface SystemApi {}
