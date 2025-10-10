import java.io.File;
import java.io.IOException;
import java.io.PrintStream;
import java.lang.reflect.AccessibleObject;
import java.lang.reflect.Constructor;
import java.lang.reflect.InaccessibleObjectException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.Callable;
import java.util.stream.Stream;

public class javarun {
    public static void main(String[] args) {
        new javarun().run(args);
    }

    private void run(String[] args) {
        if (args.length < 2) {
            help(System.err);
            System.exit(1);
        }

        String command = args[0];
        File baseDir = new File(args[1]);

        if ("scan".equals(command)) {
            scanDir(baseDir).forEach(cls -> System.out.println(cls.getName()));
            return;
        }

        if ("run".equals(command)) {
            Object[] candidateCls = scanDir(baseDir).toArray();
            long candidateClsCount = candidateCls.length;

            if (candidateClsCount == 0) {
                System.err.println("No main class found");
                System.exit(102);
            } else if (candidateClsCount > 1) {
                System.err.println("Multiple main classes found");
                System.exit(103);
            }

            Class<?> cls = (Class<?>) candidateCls[0];
            Method main = chooseLaunchableMain(cls);
            if (main == null) {
                System.err.println("No launchable main method found");
                System.exit(102);
            }

            boolean expectsArgs = (main.getParameterCount() == 1);
            boolean isStatic = Modifier.isStatic(main.getModifiers());
            String[] mainArgs = Arrays.copyOfRange(args, 2, args.length);

            // Make invocable even if not public (Java 25 allows non-private).
            makeAccessible(main);

            if (isStatic) {
                // static main
                if (expectsArgs) {
                    runOrExit(() -> {main.invoke(null, (Object) mainArgs); return null;});
                } else {
                    runOrExit(() -> {main.invoke(null); return null;});
                }
            } else {
                // instance main: class must be instantiable with a non-private no-arg ctor
                Constructor<?> ctor = requireNonPrivateNoArgCtorOrExit(cls);
                makeAccessible(ctor);
                Object target = callOrExit(ctor::newInstance);

                if (expectsArgs) {
                    runOrExit(() -> {main.invoke(target, (Object) mainArgs); return null;});
                } else {
                    runOrExit(() -> {main.invoke(target); return null;});
                }
            }
            return;
        }

        help(System.err);
        System.exit(1);
    }

    private void help(PrintStream stream) {
        stream.println("java javarun scan DIR - print classes with a launchable main() method (Java 25 rules)");
        stream.println("java javarun run  DIR - run the single launchable main() method found");
    }

    // ---------- Error handling: centralized ---------------------------------

    /*@FunctionalInterface
    private interface ThrowingRunnable { void run() throws Throwable; }

    @FunctionalInterface
    private interface ThrowingSupplier<T> { T get() throws Throwable; }*/

    private static void runOrExit(Callable<Void> action) {
        try {
            action.call();
        } catch (InvocationTargetException ex) {
            exitFromThrowable(ex.getCause());          // codes 106..113 / 2
        } catch (OutOfMemoryError ex) {
            System.exit(100);
        } catch (SecurityException ex) {
            System.exit(101);
        } catch (InaccessibleObjectException | IllegalAccessException ex) {
            System.exit(104);
        } catch (IllegalArgumentException ex) {
            System.exit(105);
        } catch (Throwable ex) {
            System.exit(1);
        }
    }

    private static <T> T callOrExit(Callable<T> action) {
        try {
            return action.call();
        } catch (InvocationTargetException ex) {
            exitFromThrowable(ex.getCause());          // codes 106..113 / 2
            return null; // unreachable
        } catch (OutOfMemoryError ex) {
            System.exit(100);
            return null;
        } catch (SecurityException ex) {
            System.exit(101);
            return null;
        } catch (InaccessibleObjectException | IllegalAccessException ex) {
            System.exit(104);
            return null;
        } catch (IllegalArgumentException ex) {
            System.exit(105);
            return null;
        } catch (Throwable ex) {
            System.exit(1);
            return null;
        }
    }

    private static void makeAccessible(AccessibleObject ao) {
        runOrExit(() -> {ao.setAccessible(true); return null;});
    }

    private static void exitFromThrowable(Throwable cause) {
        switch (cause) {
            case StackOverflowError _ -> System.exit(106);
            case ArrayIndexOutOfBoundsException _ -> System.exit(107);
            case IndexOutOfBoundsException _ -> System.exit(108);
            case NullPointerException _ -> System.exit(109);
            case ArithmeticException _ -> System.exit(110);
            case OutOfMemoryError _ -> System.exit(111);
            case SecurityException _ -> System.exit(112);
            case IOException _ -> System.exit(113);
            case null, default -> System.exit(2);
        }
    }

    // ---------- Java 25 launcher semantics ----------------------------------

    private static Method chooseLaunchableMain(Class<?> cls) {
        Method m = findMainMethod(cls, true);   // prefer main(String[])
        if (m != null) return m;
        return findMainMethod(cls, false);      // else main()
    }

    private static Method findMainMethod(Class<?> start, boolean withArgs) {
        for (Class<?> c = start; c != null; c = c.getSuperclass()) {
            Method m = findDeclaredMainOn(c, withArgs);
            if (m != null) return m;

            // Also consider interface default methods (non-static)
            Method mi = findDeclaredMainOnInterfaces(c.getInterfaces(), withArgs, new HashSet<>());
            if (mi != null) return mi;
        }
        return null;
    }

    private static Method findDeclaredMainOn(Class<?> c, boolean withArgs) {
        for (Method m : c.getDeclaredMethods()) {
            if (!m.getName().equals("main")) continue;
            if (Modifier.isPrivate(m.getModifiers())) continue;  // non-private only
            if (m.getReturnType() != void.class) continue;

            if (withArgs) {
                if (m.getParameterCount() == 1 && m.getParameterTypes()[0] == String[].class) {
                    return m;
                }
            } else {
                if (m.getParameterCount() == 0) {
                    return m;
                }
            }
        }
        return null;
    }

    private static Method findDeclaredMainOnInterfaces(Class<?>[] ifaces, boolean withArgs, Set<Class<?>> visited) {
        for (Class<?> itf : ifaces) {
            if (!visited.add(itf)) continue;

            Method m = findDeclaredMainOn(itf, withArgs);
            if (m != null && !Modifier.isStatic(m.getModifiers())) {
                // interface default (instance) main()
                return m;
            }
            Method mi = findDeclaredMainOnInterfaces(itf.getInterfaces(), withArgs, visited);
            if (mi != null) return mi;
        }
        return null;
    }

    private static boolean isLaunchable(Class<?> cls) {
        Method m = chooseLaunchableMain(cls);
        if (m == null) return false;

        if (Modifier.isStatic(m.getModifiers())) return true;

        // instance main -> class must be concrete with a non-private no-arg ctor
        if (cls.isInterface() || Modifier.isAbstract(cls.getModifiers())) return false;
        try {
            Constructor<?> ctor = cls.getDeclaredConstructor();
            return !Modifier.isPrivate(ctor.getModifiers());
        } catch (NoSuchMethodException e) {
            return false;
        }
    }

    private static Constructor<?> requireNonPrivateNoArgCtorOrExit(Class<?> cls) {
        if (cls.isInterface() || Modifier.isAbstract(cls.getModifiers())) {
            System.err.println("Class not instantiable for instance main");
            System.exit(102);
        }
        try {
            Constructor<?> ctor = cls.getDeclaredConstructor();
            if (Modifier.isPrivate(ctor.getModifiers())) {
                System.err.println("No non-private no-arg constructor for instance main");
                System.exit(102);
            }
            return ctor;
        } catch (NoSuchMethodException e) {
            System.err.println("No non-private no-arg constructor for instance main");
            System.exit(102);
            return null;
        }
    }

    // ---------- Scanning ----------------------------------------------------

    private Stream<Class<?>> scanDir(File dir) {
        final Path root = dir.toPath();

        // Load classes first into a list so we can safely close the loader.
        List<Class<?>> found = new ArrayList<>();
        try (URLClassLoader loader = new URLClassLoader(new URL[]{dir.toURI().toURL()})) {
            try (Stream<Path> paths = Files.walk(root)) {
                paths.filter(Files::isRegularFile)
                     .filter(path -> path.toString().endsWith(".class"))
                     .filter(path -> !path.getFileName().toString().equals("module-info.class"))
                     .forEach(path -> {
                         String className = toBinaryName(root, path);
                         if (className == null) return;
                         try {
                             Class<?> c = loader.loadClass(className);
                             if (!c.getName().equals(getClass().getName()) && isLaunchable(c)) {
                                 found.add(c);
                             }
                         } catch (Throwable ignore) {
                             // ignore unloadable/broken classes
                         }
                     });
            }
        } catch (IOException e) {
            assert false;
        }
        return found.stream();
    }

    private static String toBinaryName(Path root, Path classFile) {
        Path rel;
        try {
            rel = root.toAbsolutePath().normalize()
                      .relativize(classFile.toAbsolutePath().normalize());
        } catch (IllegalArgumentException ex) {
            return null;
        }
        String n = rel.toString();
        if (!n.endsWith(".class")) return null;
        String withoutExt = n.substring(0, n.length() - 6);
        return withoutExt.replace(File.separatorChar, '.'); // keep '$' for nested
    }
}

