# To Run this Dockerfile: docker can build an image by
# 1: be in directory where Dockerfile is defined
# 2. `docker build -t <new_image_name>:<tag_name> .` The `.` will build the image in current dir

# the name of the base imagename:tag to pull from
FROM python:3.9

# commands run in a new layer, become available for next steps
RUN pip install pandas ohmysportsfeedspy

# sets the working directory for instructions that follow (e.g. copy the file)
#WORKDIR /scripts

# copy from local <src> and add to container <dest>
#COPY explore.py explore.py

# allows us to execute commands when my image is run as container
# [ "<executable>", "param1", "param2" ]
#ENTRYPOINT [ "python", "-B", "explore.py" ]