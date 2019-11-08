import java.io.File;
import java.io.IOException;
import java.io.PrintStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Objects;
import java.util.regex.Pattern;
import java.util.stream.Stream;

public class javarun {
    public static void main(String[] args) {
        new javarun().run(args);
    }

    private void run(String[] args) {
        if (args.length == 0) {
            help(System.err);
            System.exit(1);
        }

        // parse arguments, first is command, second might be base directory
        String command = args[0];
        String dir = ".";
        if (args.length > 1) {
            dir = args[1];
        }

        if (command.equals("scan")) {
            scanDir(new File(dir)).forEach(cls -> System.out.println(cls.getName()));
        } else if (command.equals("run")) {
            Object[] candidateCls = scanDir(new File(dir)).toArray();
            long candidateClsCount = candidateCls.length;

            if (candidateClsCount == 0) {
                System.err.println("No main class found");
                System.exit(102);
            } else if (candidateClsCount > 1) {
                System.err.println("Multiple main classes found");
                System.exit(103);
            }

            Class<?> cls = (Class<?>) candidateCls[0];
            Method main;
            try {
                main = cls.getMethod("main", String[].class);
            } catch (NoSuchMethodException e) {
                assert false;
                return;
            }

            String[] mainArgs = Arrays.copyOfRange(args, 1, args.length);
            main.setAccessible(true);

            try {
                main.invoke(null, (Object) mainArgs);
            } catch (OutOfMemoryError ex) {
                System.exit(100);
            } catch (SecurityException ex) {
                System.exit(101);
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

        } else {
            help(System.err);
            System.exit(1);
        }
    }

    private void help(PrintStream stream) {
        stream.println("java javarun scan [dir] - print a list of classes found recursively in given directory or in current directory (if directory is not given) that contain a main() method");
        stream.println("java javarun run [dir] - run the first main() method found recursively in given directory or in current directory (if directory is not given)");
    }

    private String getClassName(Path file) {
        String[] parts = file.toString().split(Pattern.quote(File.separator));
        String[] relevant = Arrays.copyOfRange(parts, 1, parts.length);

        String name = String.join(".", relevant);
        Object className = name.substring(0, name.length() - 6); // Strip .class

        return ((String) (className));
    }

    private Stream<Class<?>> scanDir(File dir) {
        try {
            final URLClassLoader loader = new URLClassLoader(new URL[]{dir.toURI().toURL()});

            return Files.walk(dir.toPath())
                    .filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".class"))
                    .<Class<?>>map(path -> {
                        String className = getClassName(path);
                        try {
                            return loader.loadClass(className);
                        } catch (Exception e) {
                            return null;
                        }
                    })
                    .filter(Objects::nonNull)
                    .filter(cls -> !cls.getName().equals(getClass().getName()))
                    .filter(cls -> {
                        try {
                            Method method = cls.getMethod("main", String[].class);
                            return Modifier.isStatic(method.getModifiers())
                                    && Modifier.isPublic(method.getModifiers());
                        } catch (Exception e) {
                            return false;
                        }
                    });
        } catch (IOException e) {
            assert false;
            return null;
        }
    }
}
