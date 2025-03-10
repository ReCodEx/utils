/*
 * Error wrapper 1.0 for C# language in CodEx system.
 * (C) 2008 by Milan Straka & Martin Krulis
 * 
 * LICENSE: PUBLIC DOMAIN
 */

using System;
using System.IO;
using System.Reflection;

namespace CodEx {

	public class Wrapper {

		private const int RESULT_OK = 0;
		private const int RESULT_USER_ERROR = 1;

		private const int RESULT_UNHANDLED_EXCEPTION = 101;

		private const int RESULT_NULL_REFERENCE_ERROR = 102;
		private const int RESULT_MEMORY_ALLOCATION_ERROR = 103;

		private const int RESULT_INDEX_OUT_OF_RANGE_ERROR = 104;
		private const int RESULT_OVERFLOW_ERROR = 105;

		private const int RESULT_IO_ERROR = 106;
		private const int RESULT_FILE_NOT_FOUND_ERROR = 107;

		private const int RESULT_INVALID_OPERATION_ERROR = 108;

		private const int RESULT_DIVISION_BY_ZERO = 109;

		private const int RESULT_INTERNAL_ERROR = 200;
		private const int RESULT_NO_MAIN_METHOD = 201;
		private const int RESULT_MORE_MAIN_METHODS = 202;


		public static int Main(string[] args) {

			MethodInfo main = null;
			Object[] callParams = { args };

			try {
				Type[] types = Assembly.GetEntryAssembly().GetTypes();

				// We'll check all available types.
				foreach (Type type in types) {

					// We check only other classes (not our own class).
					if (type.Namespace == "CodEx")
						continue;

					// Get all public static methods named "Main".
					MemberInfo[] methods = type.FindMembers(MemberTypes.Method,
						BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static, Type.FilterName, "Main");

					if (methods.Length > ((main == null) ? 1 : 0))
						return RESULT_MORE_MAIN_METHODS;

					if (methods.Length == 1)
						main = (MethodInfo)methods[0];
				}

				// Check whether the main method was found.
				if (main == null)
					return RESULT_NO_MAIN_METHOD;

				// Fetch information about method parameters (and prepare them).
				ParameterInfo[] parameters = main.GetParameters();
				if ((parameters.Length != 1) || (parameters[0].ParameterType != typeof(string[])))
					callParams = null;

			} catch (Exception e) {
				Console.Error.WriteLine("Internal error: {0}", e.Message);
				return RESULT_INTERNAL_ERROR;
			}


			// Try to invoke user's main method and handle possible errors.
			try {
				
				// Main method is called with given parameters and return value is ignored.
				Object res = main.Invoke(null, callParams);

				// If main returned nonzero value, we return user's error code.
				if ((res != null) && (res is Int32) && ((int)res != 0))
					return RESULT_USER_ERROR;

				// If no exception were thrown we may finish peacefully.
				return RESULT_OK;

			} catch (TargetInvocationException invocationException) {
				Exception e = invocationException.InnerException;
				Console.Error.WriteLine("Unhandled {0} caught: {1}", e.GetType().FullName, e.Message);
				Console.Error.WriteLine("StackTrace:\n{0}", e.StackTrace);

				// Return exit code that corresponds to the type of thrown exception.
				if (e is NullReferenceException)	return RESULT_NULL_REFERENCE_ERROR;		else
				if (e is OutOfMemoryException)		return RESULT_MEMORY_ALLOCATION_ERROR;	else
				if (e is IndexOutOfRangeException)	return RESULT_INDEX_OUT_OF_RANGE_ERROR;	else
				if (e is OverflowException)			return RESULT_OVERFLOW_ERROR;			else
				if (e is FileNotFoundException)		return RESULT_FILE_NOT_FOUND_ERROR;		else
				if (e is IOException)				return RESULT_IO_ERROR;					else
				if (e is InvalidOperationException)	return RESULT_INVALID_OPERATION_ERROR;	else
				if (e is DivideByZeroException)		return RESULT_DIVISION_BY_ZERO;			else
					return RESULT_UNHANDLED_EXCEPTION;
			
			} catch (Exception e) {
				Console.Error.WriteLine("Unhandled {0} caught: {1}", e.GetType().FullName, e.Message);
				Console.Error.WriteLine("StackTrace:\n{0}", e.StackTrace);
				if (e is InvalidOperationException) return RESULT_INVALID_OPERATION_ERROR; else
					return RESULT_INTERNAL_ERROR;
			}

		}

	}

}
