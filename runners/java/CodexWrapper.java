
import java.io.FileInputStream;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/**
 *
 * @author Petr Hnetynka
 */
public class CodexWrapper {

  /**
   * @param args the command line arguments
   */
  public static void main(String[] args) {
    System.setSecurityManager(new SecurityManager());
    
    try {
      String mainClass = System.getProperty("codex.mainclass", "CodEx");
      
      String stdin = System.getProperty("codex.stdin");
      if (stdin != null) {
        System.setIn(new FileInputStream(stdin));
      }
      
      Class clazz = Class.forName(mainClass);
      
      Method mainMethod = clazz.getMethod("main", String[].class);
      
      Object resultToBeIgnored = mainMethod.invoke(null, (Object) args);
      
    } catch (OutOfMemoryError ex) {
      System.exit(100);
    } catch (SecurityException ex) {
      System.exit(101);
    } catch (ClassNotFoundException ex) {
      System.exit(102);
    } catch (NoSuchMethodException ex) {
      System.exit(103);
    } catch (IllegalAccessException ex) {
      System.exit(104);
    } catch (IllegalArgumentException ex) {
      System.exit(105);
    } catch (InvocationTargetException ex) {
      Throwable cause = ex.getCause();
      if (cause instanceof StackOverflowError) {
        System.exit(106);
      } else if (cause instanceof ArrayIndexOutOfBoundsException) {
        System.exit(107);
      } else if (cause instanceof IndexOutOfBoundsException) {
        System.exit(108);
      } else if (cause instanceof NullPointerException) {
        System.exit(109);
      } else if (cause instanceof ArithmeticException) {
        System.exit(110);
      } else if (cause instanceof OutOfMemoryError) {
        System.exit(111);
      } else if (cause instanceof SecurityException) {
        System.exit(112);
      } else if (cause instanceof IOException) {
        System.exit(113);
      } else {
        System.exit(2);
      }
    } catch (Throwable ex) {
      System.exit(1);
    }
  }
}
