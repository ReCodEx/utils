import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.PrintStream;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Stream;

public class javarun {
    public static void main(String[] args) {
        new javarun().run(args);
    }

    public void run(String[] args) {
        if (args.length == 0) {
            help(System.err);
            System.exit(1);
        }

        String command = args[0];

        if (command.equals("scan")) {
            scanDir(new File(".")).forEach(cls -> System.out.println(cls.getName()));
        } else if (command.equals("run")) {
            String stdin = System.getProperty("codex.stdin");
            if (stdin != null) {
                try {
                    System.setIn(new FileInputStream(stdin));
                } catch (FileNotFoundException e) {
                    System.err.printf("Input file %s was not found%n", stdin);
                }
            }

            Optional<Class<?>> cls = scanDir(new File(".")).findFirst();

            if (!cls.isPresent()) {
                System.err.println("No main class found");
                System.exit(102);
            }

            Method main;
            try {
                main = cls.get().getMethod("main", String[].class);
            } catch (NoSuchMethodException e) {
                assert false;
                return;
            }

            Object[] mainArgs = Arrays.copyOfRange(args, 1, args.length);
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

    public void help(PrintStream stream) {
        stream.println("./javarun.groovy scan - print a list of classes found in current directory (and subdirectories) that contain a main() method");
        stream.println("./javarun.groovy run - run the first main() method found in current directory (and subdirectories)");
    }

    public String getClassName(Path file) {
        String[] parts = file.toString().split("/");
        String[] relevant = Arrays.copyOfRange(parts, 1, parts.length);

        String name = String.join(".", relevant);
        Object className = name.substring(0, name.length() - 6); // Strip .class

        return ((String) (className));
    }

    public Stream<Class<?>> scanDir(File dir) {
        try {
            final URLClassLoader loader = new URLClassLoader(new URL[]{dir.toURL()});

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
