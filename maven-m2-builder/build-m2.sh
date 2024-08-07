#!/bin/bash

export JAVA_HOME=/usr/lib/jvm/jre-openjdk
export M2_HOME=/opt/maven-repo
export MAVEN_HOME=/opt/maven
export PATH=${MAVEN_HOME}/bin:${PATH}

cd `dirname "$0"` || exit 1

JAVA_VERSION=`java --version | head -1 | cut -d' ' -f2 | cut -d. -f1`
if [ -z "$JAVA_VERSION" ]; then
	echo "No Java version found."
	exit 1
fi

echo -n "Found Java $JAVA_VERSION. Is this correct? (y/N) "
read ANSWER
if [[ "$ANSWER" != 'y' && "$ANSWER" != 'Y' ]]; then
	exit
fi

cat ./ref-project/pom.xml.template | sed "s/{{JAVA_VERSION}}/${JAVA_VERSION}/g" > ./ref-project/pom.xml

rm -rf ./.m2
/opt/maven/bin/mvn -Dmaven.repo.local=./.m2 -f ./ref-project clean compile && /opt/maven/bin/mvn -Dmaven.repo.local=./.m2 -f ./ref-project exec:java && /opt/maven/bin/mvn -Dmaven.repo.local=./.m2 -f ./ref-project package && /opt/maven/bin/mvn -Dmaven.repo.local=./.m2 -f ./ref-project test
RES=$?

if [[ $RES != 0 ]]; then
	echo "Compilatio or execution failed!"
	exit $RES
fi

