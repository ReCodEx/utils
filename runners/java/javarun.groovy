#!/usr/bin/env groovy
import groovy.io.FileType
import java.lang.reflect.*

void help(stream) {
	stream.println("Sorry")
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
}

if (command.equals("run")) {
	def classes = scanDir(new File("."))
	if (classes.size() == 0) {
		System.exit(1)
	}

	def cls = classes.get(0)
	def main = cls.getMethod("main", String[].class)
	Object[] mainArgs = Arrays.copyOfRange(args, 1, args.length)
	main.setAccessible(true)

	main.invoke(null, [ mainArgs ] as Object[])
}
