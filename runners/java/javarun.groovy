#!/usr/bin/env groovy

import groovy.io.FileType
import java.lang.reflect.*

void help(stream) {
	stream.println("./javarun.groovy scan - print a list of classes found in current directory (and subdirectories) that contain a main() method")
	stream.println("./javarun.groovy run - run the first main() method found in current directory (and subdirectories)")
}

String getClassName(File file) {
	def parts = file.toString().split("/")
	def relevant = parts[1 .. parts.size() - 1]

	def name = relevant.join(".")
	def className = name.substring(0, name.length() - 6) // Strip .class

	return className
}

boolean isEntryPoint(Class<?> cls) {
	try {
		def method = cls.getMethod("main", String[].class)
		return Modifier.isStatic(method.getModifiers()) 
			and Modifier.isPublic(method.getModifiers())
	} catch (Exception e) {
		return false;
	}
}

List<String> scanDir(File dir) {
	def loader = new URLClassLoader(dir.toURL())
	def result = new ArrayList<String>()

	dir.eachFileRecurse(FileType.FILES) {
		if (it.name.endsWith(".class")) {
			def className = getClassName(it)
			def cls = loader.loadClass(className)
			if (isEntryPoint(cls)) {
				result << cls
			}
		}
	}

	return result;
}

if (args.length == 0) {
	help(System.err)
	System.exit(1)
}

def command = args[0]

if (command.equals("scan")) {
	scanDir(new File(".")).each {
		println it.getName()
	}
} else if (command.equals("run")) {
	String stdin = System.getProperty("codex.stdin");
	if (stdin != null) {
		System.setIn(new FileInputStream(stdin));
	}

	def classes = scanDir(new File("."))
	if (classes.size() == 0) {
		System.exit(1)
	}

	def cls = classes.get(0)
	def main = cls.getMethod("main", String[].class)
	Object[] mainArgs = Arrays.copyOfRange(args, 1, args.length)
	main.setAccessible(true)

	try {
		main.invoke(null, [ mainArgs ] as Object[])
	} catch (OutOfMemoryError ex) {
		System.exit(100)
	} catch (SecurityException ex) {
		System.exit(101)
	} catch (ClassNotFoundException ex) {
		System.exit(102)
	} catch (NoSuchMethodException ex) {
		System.exit(103)
	} catch (IllegalAccessException ex) {
		System.exit(104)
	} catch (IllegalArgumentException ex) {
		System.exit(105)
	} catch (InvocationTargetException ex) {
		Throwable cause = ex.getCause()
		if (cause instanceof StackOverflowError) {
			System.exit(106)
		} else if (cause instanceof ArrayIndexOutOfBoundsException) {
			System.exit(107)
		} else if (cause instanceof IndexOutOfBoundsException) {
			System.exit(108)
		} else if (cause instanceof NullPointerException) {
			System.exit(109)
		} else if (cause instanceof ArithmeticException) {
			System.exit(110)
		} else if (cause instanceof OutOfMemoryError) {
			System.exit(111)
		} else if (cause instanceof SecurityException) {
			System.exit(112)
		} else if (cause instanceof IOException) {
			System.exit(113)
		} else {
			System.exit(2)
		}
	} catch (Throwable ex) {
		System.exit(1)
	}
} else {
	help(System.err)
	System.exit(1)
}
