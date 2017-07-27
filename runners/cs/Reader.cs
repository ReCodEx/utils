namespace CodEx {

	/// <summary>
	/// Class Reader provides user friendly adaptor for reading text files and text console input.
	/// If offers simple methods to read numbers, chars and string tokens.
	/// </summary>
	public class Reader : System.IDisposable {

		#region Inicialization and destruction

		/// <summary>Initializes reader object and assigns given stream reader.</summary>
		/// <param name="s">Stream reader object used as input.</param>
		private Reader(System.IO.TextReader s) {
			stream = s;
			buf = new char[BUFLEN];
			index = 0;
			len = 0;
		}


		/// <summary>Opens given file and assigns it to created Reader object.</summary>
		/// <param name="fname">Name of the file to be opened.</param>
		public Reader(string fname) : this(new System.IO.StreamReader(fname, System.Text.Encoding.ASCII, false)) { }


		/// <summary>Static singleton value that keeps console Reader object.</summary>
		private static Reader console = null;

		/// <summary>Method providing access to universal console Reader object.</summary>
		public static Reader Console() {
			if (console == null)
				console = new Reader(System.Console.In);
			return console;
		}

		
		/// <summary>Internal disposer of reader stream.</summary>
		private void FreeStream() {
			if (stream != null) {
				((System.IDisposable)stream).Dispose();
				stream = null;
			}
		}


		/// <summary>
		/// Method that closes the reader and underlying stream object.
		/// It is recomended to use this method rather than wait for fializer.
		/// </summary>
		public void Dispose() {
			FreeStream();
			System.GC.SuppressFinalize(this);
		}


		/// <summary>Finalizer is not usually used. But if it is, it does the same as Dispose method.</summary>
		~Reader() {
			FreeStream();
		}

		#endregion


		#region Public core methods

		/// <summary>Reads one character from input.</summary>
		/// <param name="c">Output variable where the character is stored.</param>
		/// <returns>True if the reading was successfull, false otherwise.</returns>
		public bool Char(out char c) {
			if (!Update()) {
				c = '\0';
				return false;
			}
			c = buf[index++];
			return true;
		}

		
		/// <summary>Reads integer number from text file.</summary>
		/// <param name="i">Output variable where the integer is stored.</param>
		/// <returns>True if the reading was successfull, false otherwise.</returns>
		public bool Int(out int i) {
			if (!SkipSpaces()) {
				i = 0;
				return false;
			}
			i = 0;
			
			int sign = 1;
			if (buf[index] == '+')
				index++;
			else if (buf[index] == '-') {
				sign = -1;
				index++;
			}
			
			if (!Update() || !System.Char.IsDigit(buf[index]))
				throw new System.IO.IOException("No digit found when reading number.");

			while (Update() && System.Char.IsDigit(buf[index])) {
				i = i * 10 + sign * ((int)buf[index++] - (int)'0');
			}
			return true;
		}


		/// <summary>Reads real number from text file.</summary>
		/// <param name="d">Output variable where the double is stored.</param>
		/// <returns>True if the reading was successfull, false otherwise.</returns>
		public bool Double(out double d) {
			{
				int i;
				if (!Int(out i)) {
					d = 0;
					return false;
				}
				d = i;
			}

			if (Update() && buf[index] == '.') {
				index++;
				double frac = 1.0;
				while (Update() && System.Char.IsDigit(buf[index])) {
					frac /= 10.0;
					d += frac * ((int)buf[index++] - (int)'0');
				}
			}
			if (Update() && System.Char.ToLower(buf[index]) == 'e') {
				index++;
				d *= System.Math.Pow(10, Int());	// If no exponent can be parsed -> IOException.
			}
			return true;
		}


		/// <summary>Reads one string token from input. Token does not contain any blank spaces.</summary>
		/// <returns>String object containing the token or null if reading was not successfull.</returns>
		public string Word() {
			if (!SkipSpaces())
				return null;
			int start = index;
			while (index < len && !System.Char.IsWhiteSpace(buf[index]))
				index++;
			if (index < len) return new string(buf, start, index-start);
			System.Text.StringBuilder sb=new System.Text.StringBuilder();
			sb.Append(buf, start, index-start);
			while (index == len && Update()) {
				while (index < len && !System.Char.IsWhiteSpace(buf[index])) 
					index++;
				sb.Append(buf, 0, index);
			}
			return sb.ToString();
		}


		/// <summary>Reads rest of the line from input.</summary>
		/// <returns>String object containing the line or null if EOF was met.</returns>
		public string Line() {
			if (!Update())
				return null;
			int start = index;
			while (index < len && buf[index]!='\n')
				index++;
			if (index < len) return new string(buf, start, index++-start);
			System.Text.StringBuilder sb=new System.Text.StringBuilder();
			sb.Append(buf, start, index-start);
			while (index == len && Update()) {
				while (index < len && buf[index]!='\n') 
					index++;
				sb.Append(buf, 0, index);
			}
			if (index < len) index++;
			return sb.ToString();
		}

		#endregion


		#region Convenience methods

		/// <summary>Checks if the input stream ended.</summary>
		/// <returns>True if there are no more characters on the input.</returns>
		public bool EOF() {
			return !Update();
		}


		/// <summary>Skips whitespace characters and then checks for EOF.</summary>
		/// <returns>True if there are only blank characters left in the input.</returns>
		public bool SeekEOF() {
			return !SkipSpaces();
		}

		
		/// <summary>Alias for Dispose method that closes underlying stream.</summary>
		public void Close() {
			Dispose();
		}


		/// <summary>Reads one character from input. Throws IOException on error.</summary>
		/// <returns>Character that was read from the input.</returns>
		public char Char() {
			char ret; 
			if (!Char(out ret))
				throw new System.IO.IOException("Reading after EOF.");
			return ret;
		}


		/// <summary>Reads integer number from input. Throws IOException on error.</summary>
		/// <returns>Integer that was read from the input.</returns>
		public int Int() {
			int ret;
			if (!Int(out ret))
				throw new System.IO.IOException("Reading after EOF.");
			return ret;
		}


		/// <summary>Reads real number from input. Throws IOException on error.</summary>
		/// <returns>Double that was read from the input.</returns>
		public double Double() {
			double ret; 
			if (!Double(out ret))
				throw new System.IO.IOException("Reading after EOF.");
			return ret;
		}

		#endregion


		#region Fields

		/// <summary>Underlying stram object. It is not null while the stream is opened.</summary>
		private System.IO.TextReader stream;

		/// <summary>Read but unprocessed data. Null after EOF.</summary>
		private char[] buf;
		private const int BUFLEN = 16384;

		/// <summary>Actual index to the buf.</summary>
		private int index;

		/// <summary>Length of buf. Len == -1 means EOF.</summary>
		private int len;

		#endregion


		#region Private methods

		/// <summary>Ensures that index is lesser than len whenever possible.</summary>
		/// <returns>False on EOF, true otherwise.</returns>
		private bool Update() {			// 
			if (stream == null || len == -1)
				return false;
			if (index < len)
				return true;

			index = 0;
			if ((len = stream.Read(buf, 0, BUFLEN)) == 0) {
				len=-1;
				buf=null;
				return false;
			}
			return true;
		}


		/// <summary>Skip whitespaces.</summary>
		/// <returns>Returns false when EOF is found while skipping, true otherwise.</returns>
		private bool SkipSpaces() {
			while (Update()) {
				while (index < len && System.Char.IsWhiteSpace(buf[index]))
					index++;
				if (index < len)
					return true;
			}
			return false;
		}

		#endregion
	}

}
