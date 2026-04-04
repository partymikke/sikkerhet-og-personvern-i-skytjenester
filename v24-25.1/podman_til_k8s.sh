#!/bin/sh 

# Rydder opp (ved å drepe og fjerne podden -- om den finnes)
podman pod kill allpodd
podman pod rm   allpodd


########################################################
# Bygger konteinerbilder i Podmans konteinerbildearkiv #
# med kommandoer på følgende form:			   # 
# 							   #
# podman build <katalog> -t <bildenavn>                #
########################################################

podman build pseudonym-db -t pseudonym-db
podman build bidrag-db    -t bidrag-db
podman build app          -t app
podman build web          -t web


##################################################################
# Overfører bilder fra Podman til Kubernetes	             #
# Referanser:						     #
# - https://docs.podman.io/en/latest/markdown/podman-save.1.html #
# - https://microk8s.io/docs/registry-images		     #
##################################################################

podman save  pseudonym-db:latest | microk8s ctr image import -
podman save  bidrag-db:latest    | microk8s ctr image import -
podman save  app:latest          | microk8s ctr image import -
podman save  web:latest          | microk8s ctr image import -


##########################################################
# Lager og redigerer filen allpodd.yaml som brukes til å #
# iverksette systemet i Kubernetes (microk8s) 	     #
##########################################################

# Oppretter Podman-podd
podman  pod create --name allpodd -p 8080:80 -p 8081:81

# Starter konteinere, basert på konternerbildene, i den opprettede
# podden.
podman run -dit --pod=allpodd --restart=always --name app          localhost/app
podman run -dit --pod=allpodd --restart=always --name bidrag-db    localhost/bidrag-db
podman run -dit --pod=allpodd --restart=always --name pseudonym-db localhost/pseudonym-db
podman run -dit --pod=allpodd --restart=always --name web          localhost/web


# Sletter gammel kuberntes-fil -- om den finnes
rm -f ./allpodd.yaml

# Lager kubernetes-fil
podman generate kube allpodd --service -f ./allpodd.yaml

# imagePullPolicy: Never
# Ref: https://stackoverflow.com/questions/37302776/what-is-the-meaning-of-imagepullbackoff-status-on-a-kubernetes-pod
sed -i "/image:/a \    imagePullPolicy: Never" allpodd.yaml

# Rydder opp (ved å drepe og fjerne podden)
podman pod kill allpodd
podman pod rm   allpodd


########################
# Starter opp systemet #
########################

# Stoppper kjørende service og pod -- om de finnes
kubectl delete service/allpodd --grace-period=1
kubectl delete pod/allpodd     --grace-period=1

# Starte podden i en Service i K8S
kubectl create -f allpodd.yaml


####################################################
# Skriver ut info for tilgang på lokal vertsmaskin #
####################################################

echo 
echo
echo "Gjør web (80) og app (81) tilgjengelig på localhost:"
echo 
echo "microk8s kubectl port-forward service/allpodd 8080:80 &"
echo "microk8s kubectl port-forward service/allpodd 8081:81 &"
echo 
echo "For å se i nettleser, gå til http://localhost:8080"
